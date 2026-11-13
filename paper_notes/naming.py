"""Deterministic ASCII identifiers for paper files and folders."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def ascii_slug(value: str, fallback: str = "paper") -> str:
    """Return a lowercase ASCII kebab-case slug."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or fallback


def disambiguate_paper_id(candidate: str, source: Path, existing: Path) -> str:
    """Add a stable short content suffix when a candidate already belongs to another PDF."""
    target = existing / candidate
    if not target.exists():
        return candidate
    metadata = target / "metadata.json"
    if metadata.exists():
        try:
            import json

            raw = json.loads(metadata.read_text(encoding="utf-8"))
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if raw.get("sha256") == digest:
                return candidate
        except (OSError, ValueError):
            pass
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:8]
    return f"{candidate}-{digest}"


def paper_id_from_pdf(pdf: Path) -> str:
    """Id for a PDF named after its title (the `--pdf` path); `paper-notes-init` slugs the title itself."""
    return ascii_slug(pdf.stem)
