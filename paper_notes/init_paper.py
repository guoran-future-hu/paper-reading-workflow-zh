"""Create one paper's raw folder from a PDF and its title.

paper id = ASCII kebab slug of the full title. Re-running with the same PDF is a no-op.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from paper_notes.config import load_config
from paper_notes.naming import ascii_slug, disambiguate_paper_id
from paper_notes.paper_dir import update_metadata


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def init_paper(pdf: Path, title: str, evidence_root: Path, source_url: str = "") -> tuple[str, Path]:
    if not pdf.is_file():
        raise SystemExit(f"error: PDF not found: {pdf}")
    if pdf.read_bytes()[:5] != b"%PDF-":
        raise SystemExit(f"error: not a PDF (missing %PDF- header): {pdf}")
    if not title.strip():
        raise SystemExit("error: --title is empty")
    paper_id = disambiguate_paper_id(ascii_slug(title), pdf, evidence_root)
    paper_dir = evidence_root / paper_id
    (paper_dir / "text").mkdir(parents=True, exist_ok=True)
    (paper_dir / "figures" / "files").mkdir(parents=True, exist_ok=True)
    source = paper_dir / "source.pdf"
    if not source.exists():
        shutil.copy2(pdf, source)
    fields: dict[str, object] = {
        "paper_id": paper_id,
        "title": title.strip(),
        "source_pdf": f"raw/{paper_id}/source.pdf",
        "sha256": sha256_file(source),
    }
    if source_url:
        fields["source_url"] = source_url
    update_metadata(paper_dir, **fields)
    return paper_id, paper_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create raw/<paper-id>/ for one PDF; the id is the title slug.")
    parser.add_argument("--pdf", required=True, help="Trusted local PDF")
    parser.add_argument("--title", required=True, help="Exact paper title")
    parser.add_argument("--source-url", default="", help="Where the PDF came from")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    paper_id, paper_dir = init_paper(
        Path(args.pdf).expanduser().resolve(), args.title, config.inbox_evidence_root, args.source_url
    )
    print(json.dumps({
        "paper_id": paper_id,
        "paper_dir": str(paper_dir),
        "note": str(config.reading_inbox / f"{paper_id}.md"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
