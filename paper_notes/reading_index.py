"""Add or update one paper's row in <READING_INBOX>/reading-index.md, the only reading index."""
from __future__ import annotations

import argparse
import re

from paper_notes.config import load_config
from paper_notes.validate_notes import frontmatter_value

HEADER = ["# Reading Index", "", "| Paper | Year | Status | Topic |", "| --- | ---: | --- | --- |"]
ROW = re.compile(r"^\|\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*\|")


def upsert_row(index_text: str, paper_id: str, year: str, status: str, topic: str) -> str:
    """Rebuild the table: header, then rows in first-seen order, one row per paper.

    An empty topic keeps the existing row's topic.
    """
    rows: dict[str, str] = {}
    for line in index_text.splitlines():
        match = ROW.match(line.strip())
        if match:
            rows.setdefault(match.group(1).strip(), line.strip())
    if not topic and paper_id in rows:
        cells = [c.strip() for c in rows[paper_id].strip("|").split("|")]
        topic = cells[3] if len(cells) > 3 else ""
    rows[paper_id] = f"| [[{paper_id}]] | {year} | {status} | {topic.replace('|', '/')} |"
    return "\n".join(HEADER + list(rows.values())) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a finished note in the reading index.")
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--topic", default="", help="Short free-text topic label; omitted = keep the existing one")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    note = config.reading_inbox / f"{args.paper_id}.md"
    if not note.is_file():
        raise SystemExit(f"error: note not found: {note}")
    text = note.read_text(encoding="utf-8")
    index = config.reading_index
    raw = index.read_bytes().decode("utf-8") if index.exists() else ""
    newline = "\r\n" if "\r\n" in raw else "\n"
    updated = upsert_row(
        raw.replace("\r\n", "\n"), args.paper_id,
        frontmatter_value(text, "year"), frontmatter_value(text, "status") or "read", args.topic,
    )
    index.write_bytes(updated.replace("\n", newline).encode("utf-8"))
    print(f"{index}: [[{args.paper_id}]] recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
