"""Validate the paper notes in the reading inbox against their raw folders and the reading index."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paper_notes.config import load_config

PDF_SECTION = "## PDF Source"
INDEX_NAME = "reading-index.md"

RAW_ID = re.compile(r"^raw/([^/]+)/")


def fail(errors: list[str]) -> int:
    if errors:
        print("\n".join(errors))
        return 1
    print("clean notes validation: ok")
    return 0


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf'^{re.escape(key)}:\s*"(.+?)"\s*$', text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def validate_ascii_machine_fields(path: Path, text: str, errors: list[str]) -> None:
    """Keep identifiers and paths portable while allowing Unicode display metadata."""
    for key in ("paper_id", "status", "source_pdf"):
        value = frontmatter_value(text, key)
        if value and any(ord(char) > 127 for char in value):
            errors.append(f"{path.name}: {key} must be ASCII")
    if any(ord(char) > 127 for char in path.name):
        errors.append(f"{path.name}: generated note filename must be ASCII")


def note_files(notes_dir: Path, index_name: str) -> list[Path]:
    return sorted(p for p in notes_dir.glob("*.md") if p.name != index_name)


def validate_sections(path: Path, text: str, errors: list[str]) -> None:
    """Structure the pipeline owns; the body sections belong to the paper-summarizer skill."""
    headings = list(re.finditer(r"^## .*$", text, flags=re.MULTILINE))
    if not any(h.group(0).strip() == PDF_SECTION for h in headings):
        errors.append(f"{path.name}: missing heading {PDF_SECTION}")
    if len(headings) < 2:
        errors.append(f"{path.name}: no body sections besides {PDF_SECTION}")
    for current, following in zip(headings, headings[1:] + [None]):
        body = text[current.end():following.start() if following else len(text)]
        if not body.strip():
            errors.append(f"{path.name}: empty section {current.group(0).strip()}")
    if "<!-- TODO" in text:
        errors.append(f"{path.name}: unfilled scaffold marker <!-- TODO --> remains")
    if re.search(r"^\$$", text, flags=re.MULTILINE):
        errors.append(f"{path.name}: contains standalone single-dollar math delimiter")


def validate_pdf_links(notes_dir: Path, path: Path, text: str, errors: list[str]) -> None:
    """`source_pdf` and every `![[raw/...]]` embed resolve against the reading inbox."""
    source_pdf = frontmatter_value(text, "source_pdf")
    if not source_pdf:
        errors.append(f"{path.name}: missing source_pdf frontmatter")
    elif not (notes_dir / source_pdf).exists():
        errors.append(f"{path.name}: source_pdf does not exist: {source_pdf}")
    for target in re.findall(r"\[\[(raw/[^]|]+)(?:\|[^]]*)?\]\]", text):
        if not (notes_dir / target).exists():
            errors.append(f"{path.name}: missing embed target {target}")


def validate_wiki_links(notes: list[Path], texts: dict[Path, str], errors: list[str]) -> None:
    note_stems = {p.stem for p in notes}
    for path, text in texts.items():
        for match in re.finditer(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|[^]]*)?\]\]", text):
            target = match.group(1)
            if target.startswith("raw/"):
                continue
            if target not in note_stems:
                errors.append(f"{path.name}: broken note link [[{target}]]")


def manifest_expected_items(raw: object) -> int:
    """Items the note must embed: selected and not skipped."""
    items = raw.get("items", []) if isinstance(raw, dict) else []
    return sum(1 for item in items if isinstance(item, dict) and item.get("selected") and not item.get("skip"))


def note_evidence_ids(texts: dict[Path, str]) -> dict[str, list[Path]]:
    """Map each raw/<paper-id>/ referenced by a note's source_pdf to that note."""
    owners: dict[str, list[Path]] = {}
    for path, text in texts.items():
        match = RAW_ID.match(frontmatter_value(text, "source_pdf"))
        if match:
            owners.setdefault(match.group(1), []).append(path)
    return owners


def validate_figures(evidence_dir: Path, texts: dict[Path, str], errors: list[str]) -> None:
    """Each note embeds exactly its manifest's selected, unskipped items.

    The owning note is the one whose `source_pdf` names that `raw/<paper-id>/`; raw folders
    without a note yet are unfinished runs and are skipped.
    """
    for paper_id, owning in note_evidence_ids(texts).items():
        manifest = evidence_dir / paper_id / "figures" / "manifest.json"
        if not manifest.exists():
            continue
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{paper_id}: invalid figure manifest: {exc}")
            continue
        expected = manifest_expected_items(raw)
        found = sum(texts[path].count(f"raw/{paper_id}/figures/files/") for path in owning)
        if found != expected:
            errors.append(f"{paper_id}: manifest={expected}, note figure matches={found}")


EVIDENCE_FILES = ("metadata.json", "text/pruned.md", "text/references.md", "text/appendix.md")


def validate_evidence(evidence_dir: Path, texts: dict[Path, str], errors: list[str]) -> None:
    """Each note's raw folder carries the metadata and the three-way text split."""
    for paper_id, owners in note_evidence_ids(texts).items():
        paper_dir = evidence_dir / paper_id
        if not paper_dir.is_dir():
            continue
        missing = [name for name in EVIDENCE_FILES if not (paper_dir / name).is_file()]
        if missing:
            errors.append(f"{owners[0].name}: raw/{paper_id}/ lacks {', '.join(missing)}")


def validate_index(notes_dir: Path, index_name: str, notes: list[Path], errors: list[str]) -> None:
    """Every note in the reading inbox has its row in the one reading index."""
    index = notes_dir / index_name
    if not index.exists():
        errors.append(f"{index_name} missing in {notes_dir}; record each note with paper-notes-index")
        return
    listed = set(re.findall(r"\[\[([^\]|#]+)", index.read_text(encoding="utf-8")))
    for note in notes:
        if note.stem not in listed:
            errors.append(f"{note.name}: no row in {index_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the paper notes in the reading inbox.")
    parser.add_argument("--notes-dir", help="Reading inbox to validate; defaults to the config's reading_inbox")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    notes_dir = Path(args.notes_dir).expanduser().resolve() if args.notes_dir else config.reading_inbox
    errors: list[str] = []
    if not notes_dir.exists():
        errors.append(f"notes directory does not exist: {notes_dir}")
        return fail(errors)
    notes = note_files(notes_dir, INDEX_NAME)
    if not notes:
        errors.append(f"no notes found in {notes_dir}")
        return fail(errors)
    texts = {path: path.read_text(encoding="utf-8") for path in notes}
    for path, text in texts.items():
        validate_sections(path, text, errors)
        validate_ascii_machine_fields(path, text, errors)
        validate_pdf_links(notes_dir, path, text, errors)
    validate_wiki_links(notes, texts, errors)
    validate_figures(notes_dir / "raw", texts, errors)
    validate_evidence(notes_dir / "raw", texts, errors)
    validate_index(notes_dir, INDEX_NAME, notes, errors)
    return fail(errors)


if __name__ == "__main__":
    raise SystemExit(main())
