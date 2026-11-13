"""Free HTML extraction: defuddle the paper page, save its own figures, build the manifest.

Exit 2 means the URL serves no HTML version — fall back to the paid PDF path.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from paper_notes.config import load_config
from paper_notes.figure_manifest import label_kind, safe_name
from paper_notes.paper_dir import load_manifest, resolve_paper_dir, save_manifest, update_metadata

NO_HTML = 2
USER_AGENT = "Mozilla/5.0 (paper-notes)"
IMAGE = re.compile(r"!\[([^\]]*)\]\((\S+?)(?:\s+\"[^\"]*\")?\)")
CAPTION = re.compile(r"^\s*(?:\*\*)?(?:Fig(?:ure)?\.?|Table)\s*[A-Za-z]?\d+", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}\s+(.*)")
REFERENCES = re.compile(r"^(?:\d+\.?\s*)?(?:references|bibliography)\s*$", re.IGNORECASE)
PLACEHOLDER_ALT = {"", "refer to caption", "image", "figure"}


def _get(url: str, timeout: int = 60) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", b""


def has_html(url: str) -> bool:
    status, content_type, _ = _get(url)
    return status == 200 and "html" in content_type.lower()


def collect_figures(markdown: str) -> list[dict]:
    """Every image in reading order, with caption and appendix flag."""
    lines = markdown.splitlines()
    figures: list[dict] = []
    seen: set[str] = set()
    after_refs = in_appendix = False
    for index, line in enumerate(lines):
        heading = HEADING.match(line)
        if heading:
            text = heading.group(1).strip()
            if REFERENCES.match(text):
                after_refs = True
            elif after_refs or text.lower().startswith(("appendix", "supplementary")):
                in_appendix = True
        for alt, src in IMAGE.findall(line):
            if src in seen:
                continue
            seen.add(src)
            caption = "" if alt.strip().lower() in PLACEHOLDER_ALT else alt.strip()
            for following in lines[index + 1:index + 4]:
                if CAPTION.match(following):
                    caption = re.sub(r"\s+", " ", following.replace("**", "")).strip()
                    break
            figures.append({"src": src, "caption": caption[:400], "appendix": in_appendix})
    return figures


def figure_filename(ordinal: int, caption: str, src: str) -> str:
    label = label_kind(caption, "image", ordinal)
    stem = Path(urlparse(src).path)
    suffix = stem.suffix.lower() if stem.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"} else ".png"
    return f"{ordinal:03d}-{label}-{safe_name(stem.stem)}{suffix}"


def bibliography_entries(page_html: str) -> list[str]:
    """arXiv (LaTeXML) bibliography items, which defuddle drops."""
    entries = []
    for raw in re.findall(r'<li[^>]*class="ltx_bibitem[^"]*"[^>]*>(.*?)</li>', page_html, re.S):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
        if text:
            entries.append(text)
    return entries


def fill_references(markdown: str, entries: list[str]) -> str:
    """Put the entries under a References heading whose body defuddle left empty."""
    lines = markdown.splitlines(keepends=True)
    for index, line in enumerate(lines):
        heading = HEADING.match(line)
        if not heading or not REFERENCES.match(heading.group(1).strip()):
            continue
        end = next((j for j in range(index + 1, len(lines)) if HEADING.match(lines[j])), len(lines))
        if "".join(lines[index + 1:end]).strip() or not entries:
            return markdown
        body = ["\n"] + [f"- {entry}\n" for entry in entries] + ["\n"]
        return "".join(lines[:index + 1] + body + lines[end:])
    return markdown


def extract_html(paper_dir: Path, url: str) -> dict:
    out = paper_dir / "defuddle" / "full_text.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    defuddle = shutil.which("defuddle")
    if not defuddle:
        raise SystemExit("error: defuddle not on PATH")
    proc = subprocess.run([defuddle, "parse", url, "--md", "-o", str(out)], text=True, capture_output=True)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
        raise SystemExit(f"error: defuddle produced no usable text for {url}: {proc.stderr.strip()[:300]}")
    _, _, page = _get(url)
    entries = bibliography_entries(page.decode("utf-8", "replace"))
    original = out.read_text(encoding="utf-8")
    filled = fill_references(original, entries)
    out.write_text(filled, encoding="utf-8")
    restored = len(entries) if filled != original else 0

    previous = {i.get("source"): i for i in load_manifest(paper_dir).get("items", []) if isinstance(i, dict)}
    files_dir = paper_dir / "figures" / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    failures: list[str] = []
    for figure in collect_figures(out.read_text(encoding="utf-8")):
        absolute = urljoin(url if url.endswith("/") else url + "/", figure["src"])
        ordinal = len(items) + 1
        name = figure_filename(ordinal, figure["caption"], absolute)
        status, _, body = _get(absolute)
        if status != 200 or not body:
            failures.append(absolute)
            continue
        (files_dir / name).write_bytes(body)
        kind = "table" if figure["caption"].lower().startswith("table") else "image"
        item = {
            "id": ordinal,
            "type": kind,
            "caption": figure["caption"],
            "path": f"raw/{paper_dir.name}/figures/files/{name}",
            "source": absolute,
            "selected": bool(previous.get(absolute, {}).get("selected")),
        }
        if figure["appendix"]:
            item["skip"] = True
        items.append(item)
    save_manifest(paper_dir, {"items": items})
    update_metadata(paper_dir, extraction_backend="defuddle", html_url=url)
    return {"full_text": str(out), "references_restored": restored, "figures": len(items),
            "appendix_figures": sum(1 for i in items if i.get("skip")), "failed_downloads": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a paper's HTML version into its raw folder.")
    parser.add_argument("--paper-dir", required=True, help="raw/<paper-id>/ folder or bare paper id")
    parser.add_argument("--url", required=True, help="HTML version, e.g. https://arxiv.org/html/<arxiv-id>")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    paper_dir = resolve_paper_dir(args.paper_dir, load_config(args.config))
    if not has_html(args.url):
        print(json.dumps({"html": False, "url": args.url, "next": "paid PDF path"}))
        return NO_HTML
    report = extract_html(paper_dir, args.url)
    print(json.dumps({"html": True, **report}, ensure_ascii=False, indent=2))
    return 1 if report["failed_downloads"] else 0


if __name__ == "__main__":
    sys.exit(main())
