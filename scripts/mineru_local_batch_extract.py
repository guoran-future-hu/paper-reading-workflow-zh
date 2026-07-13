#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from paper_notes.config import PaperNotesConfig
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from paper_notes.config import PaperNotesConfig


def slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    return stem or "paper"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_md(result: dict, pdf: Path) -> str:
    results = result.get("results") or {}
    keys = [pdf.stem, pdf.name]
    for key in keys:
        item = results.get(key)
        if isinstance(item, dict) and item.get("md_content"):
            return str(item["md_content"])
    for item in results.values():
        if isinstance(item, dict) and item.get("md_content"):
            return str(item["md_content"])
    return ""


def extract_content_list(result: dict) -> object | None:
    for item in (result.get("results") or {}).values():
        if not isinstance(item, dict):
            continue
        content_list = item.get("content_list")
        if isinstance(content_list, str):
            try:
                return json.loads(content_list)
            except json.JSONDecodeError:
                return content_list
        if content_list is not None:
            return content_list
    return None


def extract_one(pdf: Path, paper_dir: Path, mineru_url: str, overwrite: bool) -> tuple[str, str]:
    mineru_dir = paper_dir / "mineru"
    mineru_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf, paper_dir / "source.pdf")

    result_json = mineru_dir / "result.json"
    full_text = mineru_dir / "full_text.md"
    if full_text.exists() and full_text.stat().st_size > 0 and not overwrite:
        return "cached", "full_text.md exists"

    cmd = [
        "curl",
        "-sS",
        "--max-time",
        "900",
        "-X",
        "POST",
        f"{mineru_url}/file_parse",
        "-F",
        f"files=@{pdf}",
        "-F",
        "backend=pipeline",
        "-F",
        "return_md=true",
        "-F",
        "return_middle_json=true",
        "-F",
        "return_content_list=true",
        "-o",
        str(result_json),
        "-w",
        "HTTP %{http_code} time %{time_total}s\n",
    ]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return "failed", proc.stderr.strip()

    try:
        result = json.loads(result_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return "failed", f"bad json: {exc}"

    md = extract_md(result, pdf)
    if not md.strip():
        return "failed", "md_content missing"
    full_text.write_text(md, encoding="utf-8")

    content_list = extract_content_list(result)
    if content_list is not None:
        (mineru_dir / "content_list.json").write_text(
            json.dumps(content_list, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return "done", f"{len(md)} chars; {proc.stdout.strip()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch extract PDFs through a local MinerU API.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--pdf-dir", help="Directory containing source PDFs")
    parser.add_argument("--out-root", help="Evidence output root")
    parser.add_argument("--mineru-url", help="MinerU API base URL")
    parser.add_argument("--overwrite", action="store_true", help="Re-extract even when full_text.md exists")
    args = parser.parse_args()

    config = PaperNotesConfig.from_file(args.config)
    pdf_dir = Path(args.pdf_dir).expanduser().resolve() if args.pdf_dir else config.pdf_inbox
    out_root = Path(args.out_root).expanduser().resolve() if args.out_root else config.inbox_evidence_root
    mineru_url = (args.mineru_url or config.mineru_url).rstrip("/")

    out_root.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(p for p in pdf_dir.glob("*.pdf") if p.is_file())
    seen_sha: dict[str, Path] = {}
    batch_rows: list[tuple[str, str, str, str]] = []

    for index, pdf in enumerate(pdfs, start=1):
        digest = sha256_file(pdf)
        duplicate_of = seen_sha.get(digest)
        slug = slugify(pdf.name)
        paper_dir = out_root / slug
        paper_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "source_pdf": str(pdf),
            "sha256": digest,
            "duplicate_of": str(duplicate_of) if duplicate_of else None,
            "mineru_url": mineru_url,
        }
        (paper_dir / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if duplicate_of:
            status, notes = "duplicate", "same sha as " + duplicate_of.name
            print(f"[{index}/{len(pdfs)}] duplicate: {pdf.name} == {duplicate_of.name}")
        else:
            seen_sha[digest] = pdf
            print(f"[{index}/{len(pdfs)}] extracting: {pdf.name}", flush=True)
            status, notes = extract_one(pdf, paper_dir, mineru_url, args.overwrite)
            print(f"  {status}: {notes}")
        batch_rows.append((pdf.name, slug, status, notes))

    lines = [
        "# MinerU Batch Index",
        "",
        "| PDF | Slug | Status | Notes |",
        "|---|---|---|---|",
    ]
    for pdf_name, slug, status, notes in batch_rows:
        safe_notes = str(notes).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{pdf_name}` | `{slug}` | {status} | {safe_notes} |")
    (out_root / "batch_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if all(row[2] != "failed" for row in batch_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
