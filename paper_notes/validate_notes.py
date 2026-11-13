"""Validate formal English Obsidian paper notes."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paper_notes.config import load_config

PDF_SECTION = "## PDF Source"

MACHINE_TRACE = re.compile(
    r"\b(Evidence:|Inference from|Not clearly stated|MinerU|full_text|paper_index|"
    r"evidence_cards|report\.md|完整性自检|证据锚点)\b"
)
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
    if MACHINE_TRACE.search(text):
        errors.append(f"{path.name}: contains backend/report trace wording")
    if "<!-- TODO" in text:
        errors.append(f"{path.name}: unfilled scaffold marker <!-- TODO --> remains")
    if re.search(r"^\$$", text, flags=re.MULTILINE):
        errors.append(f"{path.name}: contains standalone single-dollar math delimiter")


def _resolves(relative: str, roots: tuple[Path, ...]) -> bool:
    return any((root / relative).exists() for root in roots)


def validate_pdf_links(
    notes_dir: Path, path: Path, text: str, errors: list[str], link_roots: tuple[Path, ...] = ()
) -> None:
    """Resolve note links against the note directory and any wider vault root.

    `raw/<paper-id>/...` paths are vault-root relative (Obsidian wikilinks resolve
    vault-wide), while legacy `pdfs/...` paths sit next to the note itself.
    """
    roots = (notes_dir, *link_roots)
    source_pdf = frontmatter_value(text, "source_pdf")
    if not source_pdf:
        errors.append(f"{path.name}: missing source_pdf frontmatter")
    elif not _resolves(source_pdf, roots):
        errors.append(f"{path.name}: source_pdf does not exist: {source_pdf}")
    for target in re.findall(r"\[\[((?:pdfs|raw)/[^]|]+)(?:\|[^]]*)?\]\]", text):
        if not _resolves(target, roots):
            errors.append(f"{path.name}: missing PDF embed target {target}")


def validate_wiki_links(notes: list[Path], texts: dict[Path, str], errors: list[str]) -> None:
    note_stems = {p.stem for p in notes}
    for path, text in texts.items():
        for match in re.finditer(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|[^]]*)?\]\]", text):
            target = match.group(1)
            if target.startswith(("pdfs/", "raw/")):
                continue
            if target not in note_stems:
                errors.append(f"{path.name}: broken note link [[{target}]]")


def manifest_expected_items(raw: object) -> int:
    """Count manifest items, honoring an explicit per-item `skip: true` escape hatch."""
    items = raw.get("items", []) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    if any(isinstance(item, dict) and "selected" in item for item in items):
        return sum(
            1
            for item in items
            if isinstance(item, dict) and item.get("selected") and not item.get("skip")
        )
    return sum(1 for item in items if not (isinstance(item, dict) and item.get("skip")))


def note_evidence_ids(texts: dict[Path, str]) -> dict[str, list[Path]]:
    """Map each raw/<paper-id>/ referenced by a note's source_pdf to that note."""
    owners: dict[str, list[Path]] = {}
    for path, text in texts.items():
        match = RAW_ID.match(frontmatter_value(text, "source_pdf"))
        if match:
            owners.setdefault(match.group(1), []).append(path)
    return owners


def validate_figures(evidence_dir: Path, texts: dict[Path, str], errors: list[str]) -> None:
    """Compare each manifest against the note that declares it via `source_pdf`.

    Evidence folders belonging to papers outside the validation scope are skipped:
    `raw/` is shared by the whole vault, so a per-topic run must not fail on the
    other topics' unfinished folders.
    """
    if not evidence_dir.exists():
        return
    owners = note_evidence_ids(texts)
    for paper_dir in sorted(p for p in evidence_dir.iterdir() if p.is_dir()):
        manifest = paper_dir / "figures" / "manifest.json"
        raw_pattern = f"raw/{paper_dir.name}/figures/files/"
        legacy_pattern = f"_evidence_reports/{paper_dir.name}/extracted/figures/"
        if not manifest.exists():
            manifest = paper_dir / "extracted" / "figure_manifest.json"
            if not manifest.exists():
                continue
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{paper_dir.name}: invalid figure manifest: {exc}")
            continue
        expected = manifest_expected_items(raw)
        if not expected:
            continue
        owning = owners.get(paper_dir.name)
        if owning:
            found = sum(texts[path].count(raw_pattern) for path in owning)
        else:
            found = sum(text.count(legacy_pattern) + text.count(raw_pattern) for text in texts.values())
            if not found:
                continue
        if found != expected:
            errors.append(f"{paper_dir.name}: manifest={expected}, note figure matches={found}")


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
    parser = argparse.ArgumentParser(description="Validate clean English Obsidian paper notes.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--notes-dir", help="Directory containing formal paper notes")
    parser.add_argument("--vault-root", help="Vault root that raw/<paper-id>/ paths resolve against")
    parser.add_argument("--evidence-dir", help="Raw evidence root; defaults to <vault-root>/raw")
    parser.add_argument("--index-name", default="reading-index.md", help="Reading index file name to ignore")
    args = parser.parse_args()

    config = load_config(args.config)
    notes_dir = Path(args.notes_dir).expanduser().resolve() if args.notes_dir else config.reading_inbox
    vault_root = Path(args.vault_root).expanduser().resolve() if args.vault_root else notes_dir
    evidence_dir = Path(args.evidence_dir).expanduser().resolve() if args.evidence_dir else vault_root / "raw"

    errors: list[str] = []
    if not notes_dir.exists():
        errors.append(f"notes directory does not exist: {notes_dir}")
        return fail(errors)
    notes = note_files(notes_dir, args.index_name)
    if not notes:
        errors.append(f"no notes found in {notes_dir}")
        return fail(errors)
    texts = {path: path.read_text(encoding="utf-8") for path in notes}
    link_roots = (vault_root,) if vault_root != notes_dir else ()
    for path, text in texts.items():
        validate_sections(path, text, errors)
        validate_ascii_machine_fields(path, text, errors)
        validate_pdf_links(notes_dir, path, text, errors, link_roots)
    validate_wiki_links(notes, texts, errors)
    validate_figures(evidence_dir, texts, errors)
    validate_evidence(evidence_dir, texts, errors)
    validate_index(notes_dir, args.index_name, notes, errors)
    return fail(errors)


if __name__ == "__main__":
    raise SystemExit(main())
