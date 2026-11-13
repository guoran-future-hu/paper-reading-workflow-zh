"""Write the note skeleton: frontmatter, PDF embed, the paper-summarizer sections, the figures to place.

The body sections come from the `## Output` block of the paper-summarizer skill, so editing
that skill changes every future scaffold. Each section's guidance becomes a `<!-- TODO ... -->`
marker; the validator fails while any remain.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from paper_notes.config import load_config
from paper_notes.paper_dir import embedded_items, load_manifest, load_metadata, resolve_paper_dir

SUMMARIZER_SKILL = Path(os.environ.get(
    "PAPER_SUMMARIZER_SKILL", "~/.hermes/skills/paper-summarizer/SKILL.md"
)).expanduser()
FIGURE_LABEL = re.compile(r"^\s*(Fig(?:ure)?\.?|Table)\s*([A-Za-z]?\d+[A-Za-z]?)", re.IGNORECASE)
FIGURE_FORMAT = (
    "embed, then **<label> — <short title>.** what the figure shows, panel by panel where it has panels, "
    "then Takeaway: what it establishes for the paper's argument"
)


def figure_label(item: dict) -> str:
    match = FIGURE_LABEL.match(item.get("caption") or "")
    if match:
        kind = "Table" if match.group(1).lower().startswith("table") else "Fig."
        return f"{kind} {match.group(2)}"
    return "Table" if item.get("type") == "table" else "Fig."


def figures_to_place(items: list[dict]) -> list[str]:
    """One TODO block listing the chosen figures; each moves into the section it helps explain."""
    lines = [f"<!-- TODO Place each figure in whichever section it helps explain, as: {FIGURE_FORMAT}. "
             "Delete this block once every figure is placed."]
    for item in items:
        caption = re.sub(r"\s+", " ", item.get("caption") or "").strip().replace("-->", "->")
        lines.append(f"![[{item['path']}]]  {figure_label(item)}" + (f" | caption: {caption}" if caption else ""))
    return lines + ["-->", ""]


def _yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _todo(guidance: list[str]) -> str:
    text = " ".join(line.strip() for line in guidance if line.strip()).replace("-->", "->")
    return f"<!-- TODO {text} -->" if text else "<!-- TODO -->"


def summarizer_sections(skill_text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Parse the skill's `## Output` fenced block into (preamble guidance, [(heading, guidance)])."""
    output = re.search(r"^## Output\s*$(.*?)^```(?:md|markdown)?\s*$(.*?)^```\s*$", skill_text, re.M | re.S)
    if not output:
        raise SystemExit("error: no ```md block under '## Output' in the paper-summarizer skill")
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in output.group(2).splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            sections.append((line.strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    if not sections:
        raise SystemExit("error: the paper-summarizer Output block has no '## ' sections")
    return preamble, sections


def render_note(metadata: dict, manifest: dict, skill_text: str, authors: str, year: str,
                tags: list[str], today: str) -> str:
    paper_id = metadata["paper_id"]
    source_pdf = metadata.get("source_pdf") or f"raw/{paper_id}/source.pdf"
    preamble, sections = summarizer_sections(skill_text)
    lines = [
        "---",
        f"title: {_yaml(metadata['title'])}",
        f"authors: {_yaml(authors)}",
        f"year: {year or 'TODO'}",
        f"paper_id: {_yaml(paper_id)}",
        f"reading_date: {today}",
        "status: read",
        f"source_pdf: {_yaml(source_pdf)}",
        "tags:",
        *[f"  - {tag}" for tag in ["paper-reading", *tags]],
        "---",
        "",
        f"# {metadata['title']}",
        "",
    ]
    if any(line.strip() for line in preamble):
        lines += [_todo(preamble), ""]
    lines += ["## PDF Source", "", f"![[{source_pdf}]]", ""]
    for heading, guidance in sections:
        lines += [heading, "", _todo(guidance), ""]
    figures = embedded_items(manifest)
    if figures:
        lines += figures_to_place(figures)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold <READING_INBOX>/<paper-id>.md from the raw folder.")
    parser.add_argument("--paper-dir", required=True, help="raw/<paper-id>/ folder or bare paper id")
    parser.add_argument("--authors", default="", help="Display author list")
    parser.add_argument("--year", default="", help="Publication year")
    parser.add_argument("--tag", action="append", default=[], help="ASCII tag besides paper-reading; repeatable")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing note")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    paper_dir = resolve_paper_dir(args.paper_dir, config)
    metadata = load_metadata(paper_dir)
    if not metadata.get("title") or not metadata.get("paper_id"):
        raise SystemExit(f"error: {paper_dir}/metadata.json lacks title/paper_id; run paper-notes-init")
    if not SUMMARIZER_SKILL.is_file():
        raise SystemExit(f"error: paper-summarizer skill not found: {SUMMARIZER_SKILL} (set PAPER_SUMMARIZER_SKILL)")
    note = config.reading_inbox / f"{metadata['paper_id']}.md"
    if note.exists() and not args.force:
        raise SystemExit(f"error: {note} exists; pass --force to rebuild the skeleton (discards its text)")
    manifest = load_manifest(paper_dir)
    note.write_text(
        render_note(metadata, manifest, SUMMARIZER_SKILL.read_text(encoding="utf-8"),
                    args.authors, args.year, args.tag, dt.date.today().isoformat()),
        encoding="utf-8",
    )
    print(json.dumps({"note": str(note), "sections_from": str(SUMMARIZER_SKILL),
                      "embedded_visuals": len(embedded_items(manifest))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
