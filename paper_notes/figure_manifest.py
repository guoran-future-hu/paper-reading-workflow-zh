from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from paper_notes.config import PaperNotesConfig


def maybe_json(value: object) -> object:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def first_result(result: dict) -> dict:
    for item in (result.get("results") or {}).values():
        if isinstance(item, dict):
            return item
    return {}


def load_content_list(paper_dir: Path) -> list[dict]:
    cached = paper_dir / "mineru" / "content_list.json"
    if cached.exists():
        data = maybe_json(json.loads(cached.read_text(encoding="utf-8")))
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    result_path = paper_dir / "mineru" / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    item = first_result(result)
    data = maybe_json(item.get("content_list", []))
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def load_middle_json(paper_dir: Path) -> dict:
    result_path = paper_dir / "mineru" / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    item = first_result(result)
    data = maybe_json(item.get("middle_json", {}))
    return data if isinstance(data, dict) else {}


def clean_caption(item: dict) -> str:
    for key in ("image_caption", "table_caption", "chart_caption"):
        value = item.get(key)
        if isinstance(value, list) and value:
            return re.sub(r"\s+", " ", " ".join(str(v) for v in value)).strip()
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    body = item.get("table_body") or item.get("text") or ""
    body = re.sub(r"<[^>]+>", " ", str(body))
    return re.sub(r"\s+", " ", body).strip()[:260]


def has_visual_evidence(item: dict) -> bool:
    if item.get("type") not in {"image", "table", "chart"}:
        return False
    if not item.get("bbox") or item.get("page_idx") is None:
        return False
    caption = clean_caption(item)
    return len(caption) >= 12 or bool(item.get("table_body"))


def label_kind(caption: str, typ: str, idx: int) -> str:
    match = re.search(r"\b(Fig(?:ure)?\.?|Table)\s*([A-Za-z]?\d+[A-Za-z]?)", caption, re.IGNORECASE)
    if match:
        prefix = "figure" if match.group(1).lower().startswith(("fig", "figure")) else "table"
        return f"{prefix}-{match.group(2).lower()}"
    if typ == "table":
        return f"table-{idx:03d}"
    if typ == "chart":
        return f"chart-{idx:03d}"
    return f"figure-{idx:03d}"


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()
    return value[:80] or "visual"


def page_size_from_middle(middle: dict, page_idx: int) -> list[float]:
    pages = middle.get("pdf_info") or []
    if 0 <= page_idx < len(pages) and isinstance(pages[page_idx], dict):
        page_size = pages[page_idx].get("page_size")
        if isinstance(page_size, list) and len(page_size) >= 2:
            return [float(page_size[0]), float(page_size[1])]
    return [612.0, 792.0]


def scale_content_bbox(item: dict, page_size: list[float]) -> list[float]:
    bbox = [float(v) for v in item["bbox"]]
    sx = float(page_size[0]) / 1000.0
    sy = float(page_size[1]) / 1000.0
    return [bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy]


def render_page(pdf: Path, page_idx: int, dpi: int, tmp_dir: Path, cache: dict[int, Path]) -> Path:
    if page_idx in cache:
        return cache[page_idx]
    prefix = tmp_dir / f"page-{page_idx + 1:03d}"
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(page_idx + 1),
            "-l",
            str(page_idx + 1),
            "-r",
            str(dpi),
            "-png",
            str(pdf),
            str(prefix),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    rendered = sorted(tmp_dir.glob(f"page-{page_idx + 1:03d}-*.png"))
    if not rendered:
        raise RuntimeError(f"pdftoppm did not render page {page_idx + 1} of {pdf}")
    cache[page_idx] = rendered[0]
    return rendered[0]


def crop_visual(pdf: Path, page_idx: int, bbox: list[float], page_size: list[float], out: Path, tmp_dir: Path, cache: dict[int, Path]) -> dict:
    from PIL import Image

    dpi = 220
    margin = 18.0
    left = max(0.0, bbox[0] - margin)
    top = max(0.0, bbox[1] - margin)
    right = min(float(page_size[0]), bbox[2] + margin)
    bottom = min(float(page_size[1]), bbox[3] + margin)
    scale = dpi / 72.0
    page_img = Image.open(render_page(pdf, page_idx, dpi, tmp_dir, cache)).convert("RGB")
    crop_box = (
        int(math.floor(left * scale)),
        int(math.floor(top * scale)),
        int(math.ceil(right * scale)),
        int(math.ceil(bottom * scale)),
    )
    crop = page_img.crop(crop_box)
    out.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out)
    return {
        "status": "cropped",
        "expanded_bbox": [left, top, right, bottom],
        "dpi": dpi,
        "pixel_size": list(crop.size),
    }


def build_manifest(paper_dir: Path, crop: bool) -> dict:
    content_list = load_content_list(paper_dir)
    middle = load_middle_json(paper_dir)
    source_pdf = paper_dir / "source.pdf"
    figures_dir = paper_dir / "extracted" / "figures"
    items: list[dict] = []
    seen: set[tuple] = set()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        cache: dict[int, Path] = {}
        for idx, item in enumerate(content_list, start=1):
            if not has_visual_evidence(item):
                continue
            caption = clean_caption(item)
            page_idx = int(item["page_idx"])
            page_size = page_size_from_middle(middle, page_idx)
            bbox = scale_content_bbox(item, page_size)
            key = (
                item.get("type"),
                page_idx,
                tuple(round(float(v), 1) for v in bbox),
                caption[:120],
            )
            if key in seen:
                continue
            seen.add(key)

            label = label_kind(caption, str(item.get("type", "visual")), len(items) + 1)
            filename = f"{len(items) + 1:03d}-{safe_name(label)}.png"
            rel_path = f"extracted/figures/{filename}"
            record = {
                "id": len(items) + 1,
                "type": item.get("type"),
                "page": page_idx + 1,
                "caption": caption,
                "bbox": bbox,
                "path": rel_path,
            }
            if crop and source_pdf.exists():
                record["crop"] = crop_visual(source_pdf, page_idx, bbox, page_size, figures_dir / filename, tmp_dir, cache)
            items.append(record)

    manifest = {"items": items}
    out = paper_dir / "extracted" / "figure_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a figure/table manifest from MinerU output.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--evidence-root", help="Evidence root containing paper directories")
    parser.add_argument("--paper-dir", action="append", help="Specific evidence paper directory; repeatable")
    parser.add_argument("--crop", action="store_true", help="Crop figures from source.pdf using pdftoppm and Pillow")
    args = parser.parse_args()

    config = PaperNotesConfig.from_file(args.config)
    if args.paper_dir:
        paper_dirs = [Path(p).expanduser().resolve() for p in args.paper_dir]
    else:
        evidence_root = Path(args.evidence_root).expanduser().resolve() if args.evidence_root else config.inbox_evidence_root
        paper_dirs = sorted(p for p in evidence_root.iterdir() if p.is_dir()) if evidence_root.exists() else []

    for paper_dir in paper_dirs:
        manifest = build_manifest(paper_dir, args.crop)
        print(json.dumps({"paper_dir": str(paper_dir), "items": len(manifest["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
