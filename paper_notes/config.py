from __future__ import annotations

import json
import os
from dataclasses import dataclass
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
    mineru_url: str
    extraction_backend: str = "datalab"
    datalab_api_key: str = ""
    appendix_policy: str = "auto"
    appendix_start_page: int | None = None

    @property
    def inbox_evidence_root(self) -> Path:
        return self.reading_inbox / "raw"

    @property
    def reading_index(self) -> Path:
        return self.reading_inbox / "reading-index.md"

    @classmethod
    def defaults(cls) -> "PaperNotesConfig":
        return cls(
            pdf_inbox=env_path("PAPER_NOTES_PDF_INBOX", "./inbox/pdfs"),
            reading_inbox=env_path("PAPER_NOTES_READING_INBOX", "./vault/reading"),
            archive_root=env_path("PAPER_NOTES_ARCHIVE_ROOT", "./vault/notes"),
            mineru_url=os.environ.get("MINERU_LOCAL_URL", "http://127.0.0.1:8010").rstrip("/"),
            extraction_backend=os.environ.get("PAPER_NOTES_EXTRACTION_BACKEND", "datalab"),
            datalab_api_key=os.environ.get("DATALAB_API_KEY", ""),
            appendix_policy=os.environ.get("PAPER_NOTES_APPENDIX_POLICY", "auto"),
            appendix_start_page=(
                int(os.environ["PAPER_NOTES_APPENDIX_START_PAGE"])
                if os.environ.get("PAPER_NOTES_APPENDIX_START_PAGE")
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

        return cls(
            pdf_inbox=pick_path("pdf_inbox", base.pdf_inbox),
            reading_inbox=pick_path("reading_inbox", base.reading_inbox),
            archive_root=pick_path("archive_root", base.archive_root),
            mineru_url=str(raw.get("mineru_url", base.mineru_url)).rstrip("/"),
            extraction_backend=str(raw.get("extraction_backend", base.extraction_backend)),
            datalab_api_key=str(raw.get("datalab_api_key", base.datalab_api_key)),
            appendix_policy=str(raw.get("appendix_policy", base.appendix_policy)),
            appendix_start_page=(
                int(raw["appendix_start_page"])
                if raw.get("appendix_start_page") is not None
                else base.appendix_start_page
            ),
        )

    def to_public_dict(self) -> dict[str, Any]:
        """Config fields that are safe to print. Never include the API key."""
        return {
            "pdf_inbox": str(self.pdf_inbox),
            "reading_inbox": str(self.reading_inbox),
            "archive_root": str(self.archive_root),
            "mineru_url": self.mineru_url,
            "extraction_backend": self.extraction_backend,
            "appendix_policy": self.appendix_policy,
            "appendix_start_page": self.appendix_start_page,
        }


DEFAULT_CONFIG_NAME = "paper-notes.config.json"


def _dotenv_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return value.strip().strip("'\"")
    return ""


def load_config(path: str | os.PathLike[str] | None = None) -> PaperNotesConfig:
    """CLI entry: explicit --config, else ./paper-notes.config.json when present.

    A missing DATALAB_API_KEY is filled from the `.env` beside the config file.
    """
    if path is None and Path(DEFAULT_CONFIG_NAME).is_file():
        path = DEFAULT_CONFIG_NAME
    config = PaperNotesConfig.from_file(path)
    if not config.datalab_api_key:
        env_dir = Path(path).expanduser().resolve().parent if path else Path.cwd()
        key = _dotenv_value(env_dir / ".env", "DATALAB_API_KEY")
        if key:
            from dataclasses import replace

            config = replace(config, datalab_api_key=key)
    return config
