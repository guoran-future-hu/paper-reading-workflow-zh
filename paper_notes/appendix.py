"""Cheap, conservative appendix detection before paid PDF extraction."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppendixDetection:
    total_pages: int
    start_page: int | None = None  # one-based page number
    confidence: str = "none"
    reason: str = "no appendix heading detected"

    @property
    def page_range(self) -> str | None:
        if self.start_page is None or self.start_page <= 1:
            return None
        return f"0-{self.start_page - 2}"


_EXPLICIT = re.compile(
    r"^(?i:appendix|appendices|supplementary\s+(?:material|materials|information))"
    r"(?:\s+[A-Z](?:\.\d+)*)?(?:\s*[.:]\s*|\s+)?(?:[A-Z][^.]{0,70})?$"
)
_REFERENCES = re.compile(r"^(?:\d+\.?\s*)?(?:references|bibliography)\s*$", re.IGNORECASE)
_LETTERED = re.compile(
    r"^(?:[A-Z][.)]\s+[A-Z]\S*(?:\s+\S+){0,8}|[A-Z]\s{1,10}[A-Z][A-Z0-9\s:&,()'\-]{3,})$"
)
_LETTERED_DOT = re.compile(r"^([A-Z])\.\s+[A-Z][A-Za-z0-9\-]*(?:\s+[A-Za-z0-9&,()'\-]+){0,8}$")
_SMALL_CAPS = re.compile(r"\b([ARBS]) (PPENDIX|PPENDICES|EFERENCES|IBLIOGRAPHY|UPPLEMENTARY)\b")
MIN_START_FRACTION = 1 / 3  # a cut earlier than this is far likelier a table of contents than an appendix


def _join_small_caps(line: str) -> str:
    """'A PPENDIX' / 'R EFERENCES' (small-caps extraction) -> 'APPENDIX' / 'REFERENCES'."""
    return _SMALL_CAPS.sub(r"\1\2", line)


def _title_like(line: str) -> bool:
    return bool(line) and line[0].isupper() and len(line) < 80 and not line.endswith(".")


def _letter_heading(lines: list[str], position: int, lone_ok: bool) -> str | None:
    """'A. Title' on one line, or (after References only) a lone 'A' with the title on the next line.

    Lone letters before References are too often figure panel labels to trust.
    """
    line = lines[position]
    match = _LETTERED_DOT.match(line)
    if match:
        return match.group(1)
    if lone_ok and len(line) == 1 and line.isupper() and position + 1 < len(lines) and _title_like(lines[position + 1]):
        return line
    return None


def _lines(page: str) -> list[str]:
    return [_join_small_caps(line.strip()) for line in page.splitlines() if line.strip()]


def _is_explicit(line: str) -> bool:
    return line[:1].isupper() and not line[-1:].isdigit() and bool(_EXPLICIT.match(line))


def is_appendix_heading(text: str) -> bool:
    """An Appendix / Supplementary heading line (small caps tolerated), not a sentence mentioning one."""
    return _is_explicit(_join_small_caps(text.replace("**", "").strip()))


def _top_lines(page: str, limit: int = 18) -> list[str]:
    return _lines(page)[:limit]


def _run_pdftotext(pdf: Path, executable: str = "pdftotext") -> str:
    """Reading-order text: each column's headings land on their own lines."""
    result = subprocess.run(
        [executable, str(pdf), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def _pages(text: str) -> list[str]:
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def references_page(pages: list[str]) -> int | None:
    """Zero-based page of the References heading, anywhere on the page."""
    for index, page in enumerate(pages):
        if any(_REFERENCES.match(line) for line in _lines(page)):
            return index
    return None


def detect_appendix(pdf: Path, text: str | None = None, executable: str = "pdftotext") -> AppendixDetection:
    """Detect only high-confidence appendix starts; otherwise return no cutoff."""
    if text is None:
        text = _run_pdftotext(pdf, executable)
    pages = _pages(text)
    total_pages = len(pages)
    refs = references_page(pages)
    earliest = max(1, int(total_pages * MIN_START_FRACTION)) if total_pages > 3 else 1
    if refs is not None:
        earliest = min(earliest, max(1, refs))
    found: list[tuple[int, str]] = []

    for index, page in enumerate(pages[earliest:], start=earliest):
        if any(_is_explicit(line) for line in _lines(page)):
            found.append((index, "explicit appendix or supplementary heading"))
            break

    if refs is not None:
        for index in range(max(refs + 1, earliest), len(pages)):
            lines = _top_lines(pages[index], limit=8)
            if lines and _LETTERED.match(lines[0]):
                found.append((index, "lettered appendix heading after References"))
                break

    lettered: list[tuple[int, str]] = []
    for index in range(earliest, len(pages)):
        lines = _lines(pages[index])
        for position in range(len(lines)):
            letter = _letter_heading(lines, position, lone_ok=refs is not None and index > refs)
            if letter in ("A", "B"):
                lettered.append((index, letter))
    a_pages = sorted({i for i, letter in lettered if letter == "A"})
    b_pages = {i for i, letter in lettered if letter == "B"}
    for index in a_pages:
        if any(0 <= b - index <= 4 for b in b_pages):
            found.append((index, "lettered A/B appendix headings"))
            break

    if found:
        index, reason = min(found)
        return AppendixDetection(total_pages=total_pages, start_page=index + 1, confidence="high", reason=reason)
    return AppendixDetection(total_pages=total_pages)


def write_reference_and_appendix_text(
    pdf: Path,
    out_dir: Path,
    detection: AppendixDetection,
    executable: str = "pdftotext",
) -> tuple[Path, Path]:
    """Keep cheap local reference/appendix text available outside the paid result.

    Written as ``*-local.md`` so the formal ``text/references.md`` and
    ``text/appendix.md`` come only from the extracted-Markdown split.
    """
    text = _run_pdftotext(pdf, executable)
    pages = _pages(text)
    refs_index = references_page(pages)
    app_index = detection.start_page - 1 if detection.start_page else None
    if refs_index is None:
        references: list[str] = []
    elif app_index is not None and app_index > refs_index:
        references = pages[refs_index:app_index]
    else:
        references = pages[refs_index:]
    if app_index is None:
        appendix: list[str] = []
    elif refs_index is not None and refs_index > app_index:
        appendix = pages[app_index:refs_index]  # appendix printed before the references
    else:
        appendix = pages[app_index:]
    out_dir.mkdir(parents=True, exist_ok=True)
    references_path = out_dir / "references-local.md"
    appendix_path = out_dir / "appendix-local.md"
    references_path.write_text(
        "\n\n---\n\n".join(references) if references else "No references section detected locally.\n",
        encoding="utf-8",
    )
    appendix_path.write_text(
        "\n\n---\n\n".join(appendix) if appendix else "No appendix detected locally.\n",
        encoding="utf-8",
    )
    return references_path, appendix_path


def apply_appendix_policy(
    detection: AppendixDetection,
    policy: str = "auto",
    override_start_page: int | None = None,
) -> AppendixDetection:
    """Apply CLI policy while preserving the original detection explanation."""
    if policy not in {"auto", "full"}:
        raise ValueError("appendix policy must be 'auto' or 'full'")
    if override_start_page is not None:
        if override_start_page < 2 or override_start_page > detection.total_pages:
            raise ValueError("appendix start page must be between 2 and the document page count")
        return AppendixDetection(
            total_pages=detection.total_pages,
            start_page=override_start_page,
            confidence="override",
            reason="explicit appendix start page override",
        )
    if policy == "full":
        return AppendixDetection(
            total_pages=detection.total_pages,
            confidence="disabled",
            reason="appendix policy disabled",
        )
    return detection
