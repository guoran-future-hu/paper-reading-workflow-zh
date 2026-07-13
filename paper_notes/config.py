from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


def expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve()


def env_path(name: str, default: str) -> Path:
    return expand_path(os.environ.get(name, default))


@dataclass(frozen=True)
class PaperNotesConfig:
    pdf_inbox: Path
    reading_inbox: Path
    archive_root: Path
    staging_root: Path
    mineru_url: str
    evidence_deep_read_validator: Path | None = None

    @property
    def read_marker_dir(self) -> Path:
        return self.pdf_inbox / "已读标记"

    @property
    def inbox_evidence_root(self) -> Path:
        return self.reading_inbox / "_evidence_reports"

    @property
    def reading_index(self) -> Path:
        return self.reading_inbox / "论文阅读记录.md"

    @classmethod
    def defaults(cls) -> "PaperNotesConfig":
        return cls(
            pdf_inbox=env_path("PAPER_NOTES_PDF_INBOX", "./inbox/pdfs"),
            reading_inbox=env_path("PAPER_NOTES_READING_INBOX", "./vault/论文阅读"),
            archive_root=env_path("PAPER_NOTES_ARCHIVE_ROOT", "./vault/论文笔记"),
            staging_root=env_path("PAPER_NOTES_STAGING_ROOT", "./workspace/staging"),
            mineru_url=os.environ.get("MINERU_LOCAL_URL", "http://127.0.0.1:8010").rstrip("/"),
            evidence_deep_read_validator=(
                expand_path(os.environ["EVIDENCE_DEEP_READ_VALIDATOR"])
                if os.environ.get("EVIDENCE_DEEP_READ_VALIDATOR")
                else None
            ),
        )

    @classmethod
    def from_file(cls, path: str | os.PathLike[str] | None) -> "PaperNotesConfig":
        base = cls.defaults()
        if not path:
            return base

        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("config JSON must be an object")

        def pick_path(key: str, default: Path) -> Path:
            return expand_path(str(raw.get(key, default)))

        validator = raw.get("evidence_deep_read_validator")
        return cls(
            pdf_inbox=pick_path("pdf_inbox", base.pdf_inbox),
            reading_inbox=pick_path("reading_inbox", base.reading_inbox),
            archive_root=pick_path("archive_root", base.archive_root),
            staging_root=pick_path("staging_root", base.staging_root),
            mineru_url=str(raw.get("mineru_url", base.mineru_url)).rstrip("/"),
            evidence_deep_read_validator=expand_path(validator) if validator else base.evidence_deep_read_validator,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "pdf_inbox": str(self.pdf_inbox),
            "reading_inbox": str(self.reading_inbox),
            "archive_root": str(self.archive_root),
            "staging_root": str(self.staging_root),
            "mineru_url": self.mineru_url,
            "evidence_deep_read_validator": (
                str(self.evidence_deep_read_validator) if self.evidence_deep_read_validator else None
            ),
        }
