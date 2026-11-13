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


def paper_id(
    title: str | None = None,
    year: int | str | None = None,
    short_name: str | None = None,
    source_name: str | None = None,
) -> str:
    """Build the preferred ASCII paper id.

    A short name is used only when explicitly supplied. Without one, the full
    title (or source filename stem) is used. The year is appended when known.
    """
    base = short_name or title or (Path(source_name).stem if source_name else "paper")
    slug = ascii_slug(base)
    if year is not None and str(year).strip():
        year_slug = ascii_slug(str(year), fallback="")
        if year_slug:
            slug = f"{slug}-{year_slug}"
    return slug


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
    """Use a descriptive source filename as a safe fallback identifier."""
    return paper_id(source_name=pdf.name)
