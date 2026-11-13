"""Formal text split: extraction Markdown -> text/pruned.md, references.md, appendix.md.

Runs the prune-paper skill's split_sections.py unchanged. When the paid path never
sent the appendix pages, the pdftotext preflight copies (`*-local.md`) fill the gap.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from paper_notes.appendix import detect_appendix, is_appendix_heading, write_reference_and_appendix_text
from paper_notes.config import load_config
from paper_notes.paper_dir import resolve_paper_dir, update_metadata

SPLIT_SCRIPT = Path(os.environ.get(
    "PRUNE_PAPER_SPLIT", "~/.hermes/skills/prune-paper/scripts/split_sections.py"
)).expanduser()
SOURCES = ("defuddle", "datalab")
LOCAL_EMPTY = ("No references section detected locally.", "No appendix detected locally.")


def pick_source(paper_dir: Path) -> Path:
    for name in SOURCES:
        candidate = paper_dir / name / "full_text.md"
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    raise SystemExit(f"error: no extraction Markdown under {paper_dir}/({'|'.join(SOURCES)})/full_text.md")


def is_placeholder(text: str) -> bool:
    return text.lstrip().startswith("<!-- No")


def is_empty(text: str) -> bool:
    """No section, or a heading with no body (defuddle drops arXiv's bibliography list)."""
    return is_placeholder(text) or len(re.sub(r"^#.*$", "", text, flags=re.MULTILINE).strip()) < 50


def ensure_local_copies(paper_dir: Path) -> None:
    """The HTML path never ran the paid-path preflight; produce its free pdftotext copies now."""
    text_dir, pdf = paper_dir / "text", paper_dir / "source.pdf"
    if (text_dir / "references-local.md").exists() or not pdf.is_file():
        return
    write_reference_and_appendix_text(pdf, text_dir, detect_appendix(pdf))


def local_fallback(path: Path) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return None if text.strip() in LOCAL_EMPTY or not text.strip() else text


def run_split(source: Path, script: Path = SPLIT_SCRIPT) -> tuple[str, str, str]:
    if not script.is_file():
        raise SystemExit(f"error: prune-paper split script not found: {script} (set PRUNE_PAPER_SPLIT)")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "full_text.md"
        shutil.copy2(source, work)
        proc = subprocess.run([sys.executable, str(script), str(work)], text=True, capture_output=True)
        if proc.returncode != 0:
            raise SystemExit(f"error: split_sections.py failed: {proc.stderr.strip()[:300]}")
        parts = [Path(tmp) / f"full_text-{suffix}.md" for suffix in ("pruned", "reference", "appendix")]
        return tuple(p.read_text(encoding="utf-8") for p in parts)  # type: ignore[return-value]


def relocate_leading_appendix(pruned: str, appendix: str) -> tuple[str, str, bool]:
    """An appendix printed before References lands in the pruned body; move it out.

    The cut is the first Markdown heading that is an explicit Appendix/Supplementary heading.
    """
    lines = pruned.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("#") and is_appendix_heading(line.lstrip("#").strip()):
            moved = "".join(lines[index:])
            rest = "" if is_placeholder(appendix) else appendix
            return "".join(lines[:index]), moved + rest, True
    return pruned, appendix, False


def assemble(source_text: str, pruned: str, refs: str, appendix: str, text_dir: Path) -> tuple[dict[str, str], dict]:
    """Check the split partitions the source, then apply the local fallbacks."""
    covered = pruned + ("" if is_placeholder(refs) else refs) + ("" if is_placeholder(appendix) else appendix)
    if covered != source_text:
        raise SystemExit("error: split does not reproduce the extraction Markdown; inspect split_sections.py output")
    origin = {"references": "split", "appendix": "split"}
    pruned, appendix, moved = relocate_leading_appendix(pruned, appendix)
    if moved:
        origin["appendix"] = "moved from before References"
    if is_empty(refs) and (local := local_fallback(text_dir / "references-local.md")):
        refs, origin["references"] = local, "references-local.md"
    if is_empty(appendix) and (local := local_fallback(text_dir / "appendix-local.md")):
        appendix, origin["appendix"] = local, "appendix-local.md"
    return {"pruned.md": pruned, "references.md": refs, "appendix.md": appendix}, origin


def main() -> int:
    parser = argparse.ArgumentParser(description="Split one paper's extraction Markdown into text/.")
    parser.add_argument("--paper-dir", required=True, help="raw/<paper-id>/ folder or bare paper id")
    parser.add_argument("--force", action="store_true", help="Overwrite a text/pruned.md that was already edited")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    paper_dir = resolve_paper_dir(args.paper_dir, load_config(args.config))
    source = pick_source(paper_dir)
    text_dir = paper_dir / "text"
    text_dir.mkdir(exist_ok=True)
    pruned, refs, appendix = run_split(source)
    if is_empty(refs) or is_empty(appendix):
        ensure_local_copies(paper_dir)
    outputs, origin = assemble(source.read_text(encoding="utf-8"), pruned, refs, appendix, text_dir)

    existing = text_dir / "pruned.md"
    if existing.exists() and existing.read_text(encoding="utf-8") != outputs["pruned.md"] and not args.force:
        raise SystemExit(f"error: {existing} differs from a fresh split (already pruned?); pass --force to overwrite")
    for name, text in outputs.items():
        (text_dir / name).write_text(text, encoding="utf-8")
    update_metadata(paper_dir, text_split={"source": str(source.relative_to(paper_dir)), **origin})
    print(json.dumps({
        "source": str(source),
        **{name: len(text.splitlines()) for name, text in outputs.items()},
        "from": origin,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
