from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from paper_notes.config import load_config
from paper_notes.datalab_extract import safe_image_filename
from paper_notes.paper_dir import resolve_paper_dir


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


def load_datalab_content_list(paper_dir: Path) -> list[dict]:
    cached = paper_dir / "datalab" / "content_list.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
    return []


def load_middle_json(paper_dir: Path) -> dict:
    result_path = paper_dir / "mineru" / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    item = first_result(result)
    data = maybe_json(item.get("middle_json", {}))
    return data if isinstance(data, dict) else {}


def load_datalab_page_info(paper_dir: Path) -> dict:
    page_info_path = paper_dir / "datalab" / "page_info.json"
    if page_info_path.exists():
        return json.loads(page_info_path.read_text(encoding="utf-8"))
    return {}


def detect_backend(paper_dir: Path) -> str:
    if (paper_dir / "datalab" / "content_list.json").exists():
        return "datalab"
    if (paper_dir / "mineru" / "content_list.json").exists() or (paper_dir / "mineru" / "result.json").exists():
        return "mineru"
    return "none"


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
    # Datalab: check for pre-extracted images
    if item.get("_datalab_images"):
        return True
    # MinerU: require bbox + page_idx
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


def page_size_from_datalab(page_info: dict, page_idx: int) -> list[float]:
    """Extract page dimensions from Datalab page_info: {'0': {'bbox': [0,0,W,H]}, ...}"""
    key = str(page_idx)
    info = page_info.get(key, {}) if isinstance(page_info, dict) else {}
    bbox = info.get("bbox", [])
    if isinstance(bbox, list) and len(bbox) >= 4:
        return [float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])]
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


CAPTION_LINE = re.compile(r"^\s*(?:\*\*)?(?:Fig(?:ure)?\.?|Table)\s*[A-Za-z]?\d+", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().lower()


def paper_caption(full_text: str, image_name: str, description: str = "") -> str:
    """The paper's own caption near an image in the extraction Markdown.

    Datalab writes its generated image description into the alt text and repeats it as a
    plain line; the paper's caption follows. Skip anything matching the description.
    """
    lines = full_text.splitlines()
    for index, line in enumerate(lines):
        if f"]({image_name})" not in line:
            continue
        alt = re.search(r"!\[(.*)\]\(" + re.escape(image_name) + r"\)", line)
        skip = {_norm(description), _norm(alt.group(1)) if alt else ""} - {""}
        for following in lines[index + 1:index + 12]:
            if CAPTION_LINE.match(following) and _norm(following) not in skip:
                return re.sub(r"\s+", " ", following.replace("**", "")).strip()
        return ""
    return ""


def build_manifest(paper_dir: Path, crop: bool) -> dict:
    backend = detect_backend(paper_dir)
    if backend == "none":
        raise SystemExit(f"error: {paper_dir} has no datalab/ or mineru/ extraction "
                         "(the HTML path's manifest comes from paper-notes-extract-html)")
    if backend == "datalab":
        content_list = load_datalab_content_list(paper_dir)
        page_info = load_datalab_page_info(paper_dir)
    else:
        content_list = load_content_list(paper_dir)
        page_info = load_middle_json(paper_dir)
    source_pdf = paper_dir / "source.pdf"
    figures_dir = paper_dir / "figures" / "files"
    is_datalab = backend == "datalab"
    metadata_path = paper_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    appendix_start_page = metadata.get("appendix_start_page")
    full_text_path = paper_dir / backend / "full_text.md"
    full_text = full_text_path.read_text(encoding="utf-8") if full_text_path.exists() else ""
    items: list[dict] = []
    seen: set[tuple] = set()
    datalab_image_ordinal = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        cache: dict[int, Path] = {}
        for idx, item in enumerate(content_list, start=1):
            if not has_visual_evidence(item):
                continue
            caption = clean_caption(item)
            page_idx = int(item.get("page_idx", 0))
            page_number = page_idx + 1

            if is_datalab:
                page_size = page_size_from_datalab(page_info, page_idx)
                # Datalab bbox is already in page coordinates, no scaling needed
                if item.get("bbox"):
                    bbox = [float(v) for v in item["bbox"]]
                else:
                    bbox = [0.0, 0.0, page_size[0], page_size[1]]
            else:
                page_size = page_size_from_middle(page_info, page_idx)
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

            description = ""
            if is_datalab and item.get("_datalab_images"):
                found_caption = paper_caption(full_text, str(next(iter(item["_datalab_images"]))), caption)
                description, caption = caption, found_caption

            label = label_kind(caption, str(item.get("type", "visual")), len(items) + 1)

            # For datalab: use the pre-extracted image filename
            if is_datalab and item.get("_datalab_images"):
                datalab_image_ordinal += 1
                img_name = next(iter(item["_datalab_images"]))
                filename = safe_image_filename(str(img_name), datalab_image_ordinal)
                original_image = figures_dir.parent.parent / "extracted" / "figures" / str(img_name)
                if original_image.exists() and original_image != figures_dir / filename:
                    figures_dir.mkdir(parents=True, exist_ok=True)
                    original_image.replace(figures_dir / filename)
                rel_path = f"raw/{paper_dir.name}/figures/files/{filename}"
            elif is_datalab:
                # Datalab tables without images: generate a name but mark skip
                filename = f"{len(items) + 1:03d}-{safe_name(label)}.png"
                rel_path = f"raw/{paper_dir.name}/figures/files/{filename}"
            else:
                filename = f"{len(items) + 1:03d}-{safe_name(label)}.png"
                rel_path = f"raw/{paper_dir.name}/figures/files/{filename}"

            record = {
                "id": len(items) + 1,
                "type": item.get("type"),
                "page": page_number,
                "caption": caption,
                "bbox": bbox,
                "path": rel_path,
                "selected": False,
            }
            if description and _norm(description) != _norm(caption):
                record["extractor_description"] = description  # generated by the extractor, not the paper
            # Datalab tables without pre-extracted images: mark skip so validator ignores them
            if is_datalab and item.get("type") == "table" and not item.get("_datalab_images"):
                record["skip"] = True
            if appendix_start_page and page_number >= int(appendix_start_page):
                record["skip"] = True
            if crop and source_pdf.exists() and not is_datalab:
                record["crop"] = crop_visual(source_pdf, page_idx, bbox, page_size, figures_dir / filename, tmp_dir, cache)
            items.append(record)

    manifest = {"items": items}
    out = paper_dir / "figures" / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a figure/table manifest from MinerU output.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--evidence-root", help="Evidence root containing paper directories")
    parser.add_argument("--paper-dir", action="append", help="Specific evidence paper directory; repeatable")
    parser.add_argument("--crop", action="store_true", help="Crop figures from source.pdf using pdftoppm and Pillow")
    parser.add_argument("--select-id", action="append", type=int, default=[], help="Mark a manifest item as selected; repeatable")
    args = parser.parse_args()
    if not args.paper_dir and not args.evidence_root:
        parser.error("name --paper-dir <raw folder> (or --evidence-root to rebuild every manifest under it)")

    config = load_config(args.config)
    if args.paper_dir:
        paper_dirs = [resolve_paper_dir(p, config) for p in args.paper_dir]
    else:
        evidence_root = Path(args.evidence_root).expanduser().resolve()
        paper_dirs = sorted(p for p in evidence_root.iterdir() if p.is_dir()) if evidence_root.exists() else []

    for paper_dir in paper_dirs:
        previous_manifest = paper_dir / "figures" / "manifest.json"
        previous_selected: dict[int, bool] = {}
        if previous_manifest.exists() and not args.select_id:
            try:
                previous_raw = json.loads(previous_manifest.read_text(encoding="utf-8"))
                previous_selected = {
                    int(item["id"]): bool(item.get("selected"))
                    for item in previous_raw.get("items", [])
                    if isinstance(item, dict) and "id" in item
                }
            except (OSError, ValueError, TypeError):
                previous_selected = {}
        manifest = build_manifest(paper_dir, args.crop)
        if args.select_id:
            for item in manifest["items"]:
                item["selected"] = item.get("id") in set(args.select_id)
        elif previous_selected:
            for item in manifest["items"]:
                item["selected"] = previous_selected.get(int(item["id"]), False)
            (paper_dir / "figures" / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps({"paper_dir": str(paper_dir), "items": len(manifest["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
