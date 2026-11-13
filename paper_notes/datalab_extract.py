from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from paper_notes.appendix import apply_appendix_policy, detect_appendix, write_reference_and_appendix_text
from paper_notes.config import load_config
from paper_notes.naming import disambiguate_paper_id, paper_id_from_pdf
from paper_notes.paper_dir import resolve_paper_dir, update_metadata


def slugify(name: str) -> str:
    return paper_id_from_pdf(Path(name))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---- Chunks → MinerU content_list mapping ----


def _block_type_to_mineru(block_type: str) -> str:
    mapping = {
        "Picture": "image",
        "Figure": "image",
        "Diagram": "image",
        "Table": "table",
        "Chart": "chart",
    }
    return mapping.get(block_type, block_type.lower())


def _extract_alt_from_html(html: str) -> str:
    m = re.search(r'alt="([^"]*)"', html)
    if m:
        return m.group(1)
    m = re.search(r"alt='([^']*)'", html)
    return m.group(1) if m else ""


def safe_image_filename(original: str, ordinal: int) -> str:
    suffix = Path(original).suffix.lower() or ".png"
    stem = re.sub(r"[^a-z0-9-]+", "-", Path(original).stem.lower()).strip("-") or "image"
    return f"{ordinal:03d}-{stem}{suffix}"


def build_content_list(chunks: dict) -> list[dict]:
    """Map Datalab chunks blocks to MinerU-style content_list entries."""
    blocks = chunks.get("blocks", [])
    content_list: list[dict] = []
    for block in blocks:
        btype = block.get("block_type", "")
        mineru_type = _block_type_to_mineru(btype)
        if mineru_type not in ("image", "table", "chart"):
            continue
        entry: dict = {
            "type": mineru_type,
            "bbox": block.get("bbox", []),
            "page_idx": block.get("page", 0),
        }
        # Caption from alt text
        alt = _extract_alt_from_html(block.get("html", ""))
        if mineru_type == "image":
            entry["image_caption"] = [alt] if alt else []
        elif mineru_type == "table":
            entry["table_caption"] = [alt] if alt else []
            entry["table_body"] = block.get("html", "")
        elif mineru_type == "chart":
            entry["chart_caption"] = [alt] if alt else []
        # Map image keys to paths
        images = block.get("images", {})
        if images:
            entry["_datalab_images"] = images
        content_list.append(entry)
    return content_list


# ---- Image saving ----


def save_datalab_images(chunks: dict, figures_dir: Path) -> int:
    """Save base64 images from chunks blocks to the figures directory. Returns count."""
    import base64

    blocks = chunks.get("blocks", [])
    seen: set[str] = set()
    saved = 0
    figures_dir.mkdir(parents=True, exist_ok=True)
    for block in blocks:
        for filename, b64data in block.get("images", {}).items():
            if filename in seen:
                continue
            seen.add(filename)
            try:
                safe_filename = safe_image_filename(str(filename), saved + 1)
                (figures_dir / safe_filename).write_bytes(base64.b64decode(b64data))
                saved += 1
            except Exception:
                pass
    return saved


# ---- Single paper extraction ----


def extract_one(
    pdf: Path,
    paper_dir: Path,
    datalab_api_key: str,
    overwrite: bool = False,
    mode: str = "fast",
    appendix_policy: str = "auto",
    appendix_start_page: int | None = None,
) -> tuple[str, str]:
    """Extract one PDF via Datalab API.

    Returns (status, notes) like mineru_extract.extract_one().
    """
    from datalab_sdk import ConvertOptions, DatalabClient

    datalab_dir = paper_dir / "datalab"
    datalab_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "text").mkdir(parents=True, exist_ok=True)
    figures_dir = paper_dir / "figures" / "files"
    figures_dir.mkdir(parents=True, exist_ok=True)
    source = paper_dir / "source.pdf"
    if not source.exists() or source.resolve() != pdf.resolve():
        shutil.copy2(pdf, source)

    result_json = datalab_dir / "result.json"
    full_text = datalab_dir / "full_text.md"
    content_list_json = datalab_dir / "content_list.json"
    page_info_json = datalab_dir / "page_info.json"

    try:
        detection = apply_appendix_policy(
            detect_appendix(pdf), appendix_policy, appendix_start_page
        )
        write_reference_and_appendix_text(pdf, paper_dir / "text", detection)
        metadata_path = paper_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        metadata.update(
            {
                "total_pages": detection.total_pages,
                "processed_page_range": detection.page_range,
                "appendix_start_page": detection.start_page,
                "appendix_confidence": detection.confidence,
                "appendix_reason": detection.reason,
            }
        )
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if full_text.exists() and full_text.stat().st_size > 0 and not overwrite:
            return "cached", "full_text.md exists"

        if not datalab_api_key:
            return "failed", "DATALAB_API_KEY not set"

        client = DatalabClient(api_key=datalab_api_key)
        option_kwargs = {
            "output_format": "markdown,chunks",
            "mode": mode,
            "page_range": detection.page_range,
            "paginate": True,
            "disable_image_captions": True,
        }
        try:
            options = ConvertOptions(**option_kwargs)
        except TypeError:
            # Older SDKs may not expose synthetic-caption suppression.
            option_kwargs.pop("disable_image_captions", None)
            options = ConvertOptions(**option_kwargs)
        result = client.convert(file_path=pdf, options=options)
    except Exception as exc:
        return "failed", str(exc)

    if not result.success:
        return "failed", result.error or "unknown Datalab error"

    # Save full_text.md
    md = result.markdown or ""
    if not md.strip():
        return "failed", "markdown content missing"
    full_text.write_text(md, encoding="utf-8")

    # Save stripped result.json (no images to keep it small)
    result_dict = {
        "success": result.success,
        "output_format": result.output_format,
        "page_count": result.page_count,
        "runtime": result.runtime,
        "cost_breakdown": result.cost_breakdown,
        "status": result.status,
    }
    result_json.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Build and save content_list.json from chunks
    chunks = result.chunks or {}
    content_list = build_content_list(chunks)
    content_list_json.write_text(json.dumps(content_list, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Save page_info.json
    page_info = chunks.get("page_info", {})
    if page_info:
        page_info_json.write_text(json.dumps(page_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Save images
    saved_imgs = save_datalab_images(chunks, figures_dir)

    notes = f"{len(md)} chars, {len(content_list)} visuals, {saved_imgs} images"
    if result.cost_breakdown:
        cost = result.cost_breakdown.get("final_cost_cents")
        if isinstance(cost, (int, float)):
            notes += f", ${cost / 100:.4f}"
    return "done", notes


# ---- Batch mode ----


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch extract PDFs through Datalab API.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--paper-dir", action="append", default=[],
                        help="Initialised raw/<paper-id>/ folder (or bare id); extracts its source.pdf in place")
    parser.add_argument("--pdf", action="append", default=[], help="One source PDF to extract; repeatable")
    parser.add_argument("--pdf-dir", help="Directory whose every PDF is extracted (paid per file)")
    parser.add_argument("--out-root", help="Evidence output root")
    parser.add_argument("--api-key", help="Datalab API key (or set DATALAB_API_KEY env)")
    parser.add_argument("--mode", default="fast", choices=["fast", "balanced", "accurate"], help="Datalab extraction mode")
    parser.add_argument("--appendix-policy", choices=["auto", "full"], default=None)
    parser.add_argument("--appendix-start-page", type=int, help="One-based appendix start page override")
    parser.add_argument("--overwrite", action="store_true", help="Re-extract even when full_text.md exists")
    args = parser.parse_args()

    if not args.pdf and not args.pdf_dir and not args.paper_dir:
        parser.error("name the input with --paper-dir <raw folder>, --pdf <file> or --pdf-dir <dir>; "
                     "the PDF inbox is never batch-extracted implicitly")
    config = load_config(args.config)
    out_root = Path(args.out_root).expanduser().resolve() if args.out_root else config.inbox_evidence_root
    api_key = args.api_key or config.datalab_api_key
    appendix_policy = args.appendix_policy or config.appendix_policy
    appendix_start_page = args.appendix_start_page if args.appendix_start_page is not None else config.appendix_start_page

    out_root.mkdir(parents=True, exist_ok=True)
    pdfs = [Path(p).expanduser().resolve() for p in args.pdf]
    missing = [p for p in pdfs if not p.is_file()]
    if missing:
        parser.error("PDF not found: " + ", ".join(str(p) for p in missing))
    if args.pdf_dir:
        pdfs += sorted(p for p in Path(args.pdf_dir).expanduser().resolve().glob("*.pdf") if p.is_file())
    targets: list[tuple[Path, str]] = []
    for value in args.paper_dir:
        paper_dir = resolve_paper_dir(value, config)
        if not (paper_dir / "source.pdf").is_file():
            parser.error(f"no source.pdf in {paper_dir}; run paper-notes-init first")
        targets.append((paper_dir / "source.pdf", paper_dir.name))
    for pdf in pdfs:
        targets.append((pdf, disambiguate_paper_id(slugify(pdf.name), pdf, out_root)))
    seen_sha: dict[str, Path] = {}
    batch_rows: list[tuple[str, str, str, str]] = []

    for index, (pdf, slug) in enumerate(targets, start=1):
        digest = sha256_file(pdf)
        duplicate_of = seen_sha.get(digest)
        paper_dir = out_root / slug
        paper_dir.mkdir(parents=True, exist_ok=True)

        update_metadata(
            paper_dir,
            paper_id=slug,
            source_pdf=f"raw/{slug}/source.pdf",
            sha256=digest,
            extraction_backend="datalab",
            mode=args.mode,
            appendix_policy=appendix_policy,
        )

        if duplicate_of:
            status, notes = "duplicate", "same sha as " + duplicate_of.name
            print(f"[{index}/{len(targets)}] duplicate: {pdf.name} == {duplicate_of.name}")
        else:
            seen_sha[digest] = pdf
            print(f"[{index}/{len(targets)}] extracting: {slug}", flush=True)
            status, notes = extract_one(
                pdf,
                paper_dir,
                api_key,
                args.overwrite,
                mode=args.mode,
                appendix_policy=appendix_policy,
                appendix_start_page=appendix_start_page,
            )
            print(f"  {status}: {notes}")
        batch_rows.append((pdf.name, slug, status, notes))

    return 0 if all(row[2] != "failed" for row in batch_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
