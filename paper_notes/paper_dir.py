"""One paper's raw folder: `<READING_INBOX>/raw/<paper-id>/` and its metadata."""
from __future__ import annotations

import json
from pathlib import Path

from paper_notes.config import PaperNotesConfig

TEXT_FILES = ("pruned.md", "references.md", "appendix.md")


def resolve_paper_dir(value: str, config: PaperNotesConfig) -> Path:
    """Accept a raw folder path or a bare paper id."""
    path = Path(value).expanduser()
    if path.is_dir():
        return path.resolve()
    candidate = config.inbox_evidence_root / value
    if candidate.is_dir():
        return candidate
    raise SystemExit(f"error: no raw folder for {value!r} (looked in {config.inbox_evidence_root})")


def load_metadata(paper_dir: Path) -> dict:
    path = paper_dir / "metadata.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def update_metadata(paper_dir: Path, **fields: object) -> dict:
    """Merge fields into metadata.json; other steps' keys survive."""
    metadata = load_metadata(paper_dir)
    metadata.update(fields)
    (paper_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def load_manifest(paper_dir: Path) -> dict:
    path = paper_dir / "figures" / "manifest.json"
    if not path.exists():
        return {"items": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"items": data if isinstance(data, list) else []}


def save_manifest(paper_dir: Path, manifest: dict) -> None:
    path = paper_dir / "figures" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def embedded_items(manifest: dict) -> list[dict]:
    """Items the note's section 5 must embed — the validator's count."""
    return [i for i in manifest.get("items", []) if isinstance(i, dict) and i.get("selected") and not i.get("skip")]
