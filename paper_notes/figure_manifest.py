"""Build figures/manifest.json from a Datalab extraction (the HTML path builds its own)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paper_notes.config import load_config
from paper_notes.datalab_extract import safe_image_filename
from paper_notes.paper_dir import load_manifest, resolve_paper_dir, save_manifest

CAPTION_LINE = re.compile(r"^\s*(?:\*\*)?(?:Fig(?:ure)?\.?|Table)\s*[A-Za-z]?\d+", re.IGNORECASE)


def _load_json(path: Path, default):  # noqa: ANN001 - JSON of any shape
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


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
    if item.get("_datalab_images"):
        return True
    if not item.get("bbox") or item.get("page_idx") is None:
        return False
    return len(clean_caption(item)) >= 12 or bool(item.get("table_body"))


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


def build_manifest(paper_dir: Path) -> dict:
    datalab = paper_dir / "datalab"
    if not (datalab / "content_list.json").exists():
        raise SystemExit(f"error: {paper_dir} has no datalab/content_list.json "
                         "(the HTML path's manifest comes from paper-notes-extract-html)")
    content_list = [i for i in _load_json(datalab / "content_list.json", []) if isinstance(i, dict)]
    full_text = (datalab / "full_text.md").read_text(encoding="utf-8") if (datalab / "full_text.md").exists() else ""
    appendix_start_page = _load_json(paper_dir / "metadata.json", {}).get("appendix_start_page")
    figures_dir = paper_dir / "figures" / "files"
    items: list[dict] = []
    seen: set[tuple] = set()
    image_ordinal = 0

    for item in content_list:
        if not has_visual_evidence(item):
            continue
        caption = clean_caption(item)
        page_number = int(item.get("page_idx", 0)) + 1
        bbox = [float(v) for v in item.get("bbox") or []]
        key = (item.get("type"), page_number, tuple(round(v, 1) for v in bbox), caption[:120])
        if key in seen:
            continue
        seen.add(key)

        images = item.get("_datalab_images")
        description = ""
        if images:
            image_name = str(next(iter(images)))
            description, caption = caption, paper_caption(full_text, image_name, caption)
            image_ordinal += 1
            filename = safe_image_filename(image_name, image_ordinal)
            original = paper_dir / "extracted" / "figures" / image_name
            if original.exists() and original != figures_dir / filename:
                figures_dir.mkdir(parents=True, exist_ok=True)
                original.replace(figures_dir / filename)
        else:
            label = label_kind(caption, str(item.get("type", "visual")), len(items) + 1)
            filename = f"{len(items) + 1:03d}-{safe_name(label)}.png"

        record = {
            "id": len(items) + 1,
            "type": item.get("type"),
            "page": page_number,
            "caption": caption,
            "bbox": bbox,
            "path": f"raw/{paper_dir.name}/figures/files/{filename}",
            "selected": False,
        }
        if description and _norm(description) != _norm(caption):
            record["extractor_description"] = description  # generated by the extractor, not the paper
        if not images:
            record["skip"] = True  # a table Datalab returned as text only: nothing to embed
        if appendix_start_page and page_number >= int(appendix_start_page):
            record["skip"] = True
        items.append(record)
    return {"items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build figures/manifest.json from a paper's Datalab extraction.")
    parser.add_argument("--paper-dir", action="append", required=True, help="raw/<paper-id>/ folder or bare id; repeatable")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    for paper_dir in [resolve_paper_dir(p, config) for p in args.paper_dir]:
        previous = {int(i["id"]): bool(i.get("selected")) for i in load_manifest(paper_dir).get("items", [])
                    if isinstance(i, dict) and "id" in i}
        manifest = build_manifest(paper_dir)
        for item in manifest["items"]:
            item["selected"] = previous.get(item["id"], False)
        save_manifest(paper_dir, manifest)
        print(json.dumps({"paper_dir": str(paper_dir), "items": len(manifest["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
