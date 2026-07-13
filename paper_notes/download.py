"""Resolve a paper with opencli adapters and download its PDF."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from paper_notes.config import PaperNotesConfig


def arxiv_pdf_from_id(arxiv_id: str) -> str:
    clean = re.sub(r"v\d+$", "", arxiv_id.strip(), flags=re.IGNORECASE)
    return f"https://arxiv.org/pdf/{clean}"


def normalize_title(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def title_match_score(query: str, title: str) -> float:
    query_norm = normalize_title(query)
    title_norm = normalize_title(title)
    if not query_norm or not title_norm:
        return 0.0
    if query_norm == title_norm:
        return 1.0

    query_words = set(query_norm.split())
    title_words = set(title_norm.split())
    if not query_words or not title_words:
        return 0.0

    coverage = len(query_words & title_words) / len(query_words)
    extra_words = len(title_words - query_words)
    if coverage == 1.0 and extra_words <= 2:
        return 0.94
    return coverage * 0.85


def run_json(cmd: list[str]) -> list[dict]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "command failed: " + " ".join(cmd))
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non-JSON output from {' '.join(cmd)}: {exc}") from exc
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def arxiv_id_from_text(text: str) -> str | None:
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"\barXiv[:\s]*([0-9]{4}\.[0-9]{4,5})(?:v\d+)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    # A bare ID is only trusted when the whole query is the ID; otherwise a
    # title that merely contains an ID-shaped number would skip title search.
    match = re.fullmatch(r"([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", text.strip())
    if match:
        return match.group(1)
    return None


def pdf_url_from_url(url: str) -> str:
    if re.search(r"\.pdf(?:$|[?#])", url, flags=re.IGNORECASE):
        return url
    match = re.search(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", url, flags=re.IGNORECASE)
    if match:
        return arxiv_pdf_from_id(match.group(1))
    match = re.search(r"arxiv\.org/pdf/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", url, flags=re.IGNORECASE)
    if match:
        return arxiv_pdf_from_id(match.group(1))
    return url


def sanitize_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:180] or "paper"


def enrich_arxiv_row(row: dict) -> dict:
    enriched = dict(row)
    if enriched.get("pdf"):
        return enriched
    url = str(enriched.get("url", ""))
    if url:
        pdf = pdf_url_from_url(url)
        if re.search(r"arxiv\.org/pdf/", pdf, flags=re.IGNORECASE):
            enriched["pdf"] = pdf
            return enriched
    if enriched.get("id"):
        enriched["pdf"] = arxiv_pdf_from_id(str(enriched["id"]))
    return enriched


def arxiv_paper(arxiv_id: str) -> dict:
    rows = run_json(["opencli", "arxiv", "paper", arxiv_id, "-f", "json"])
    if not rows:
        raise RuntimeError(f"opencli arxiv paper returned no rows for {arxiv_id}")
    return enrich_arxiv_row(rows[0])


def select_arxiv_candidate(query: str, rows: list[dict]) -> tuple[dict | None, list[tuple[float, dict]]]:
    scored = [(title_match_score(query, str(row.get("title", ""))), row) for row in rows]
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return None, []
    best_score, best_row = scored[0]
    if best_score >= 0.92:
        return enrich_arxiv_row(best_row), scored
    return None, scored


def arxiv_search(query: str, limit: int) -> dict:
    rows = run_json(["opencli", "arxiv", "search", query, "--limit", str(limit), "-f", "json"])
    if not rows:
        raise RuntimeError(f"opencli arxiv search returned no rows for {query!r}")
    candidate, scored = select_arxiv_candidate(query, rows)
    if candidate:
        return candidate

    stripped = query.strip()
    if not (stripped.startswith('"') and stripped.endswith('"')):
        quoted_query = f'"{stripped}"'
        quoted_rows = run_json(["opencli", "arxiv", "search", quoted_query, "--limit", str(limit), "-f", "json"])
        if quoted_rows:
            candidate, quoted_scored = select_arxiv_candidate(query, quoted_rows)
            if candidate:
                return candidate
            scored = quoted_scored + scored

    candidates = [
        {"id": row.get("id"), "title": row.get("title"), "url": row.get("url")}
        for _, row in scored[: min(5, len(scored))]
    ]
    raise RuntimeError(
        "no high-confidence arXiv title match; use an arXiv ID/URL or inspect candidates: "
        + json.dumps(candidates, ensure_ascii=False)
    )


def resolve(query: str | None, url: str | None, limit: int) -> tuple[str, str, dict]:
    if url:
        pdf = pdf_url_from_url(url)
        title = Path(urlparse(pdf).path).stem or "paper"
        return pdf, title, {"source": "url", "url": url}
    if not query:
        raise RuntimeError("provide --query or --url")
    arxiv_id = arxiv_id_from_text(query)
    if arxiv_id:
        row = arxiv_paper(arxiv_id)
        return row.get("pdf") or arxiv_pdf_from_id(arxiv_id), row.get("title") or arxiv_id, row
    row = arxiv_search(query, limit)
    pdf = row.get("pdf")
    if not pdf:
        raise RuntimeError(f"best arXiv candidate has no PDF URL: {row}")
    return pdf, row.get("title") or query, row


def download(pdf_url: str, title: str, out_dir: Path, dry_run: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(title)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    out = out_dir / filename
    if dry_run:
        print(json.dumps({"pdf_url": pdf_url, "output": str(out)}, ensure_ascii=False, indent=2))
        return out
    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "2",
        "--connect-timeout",
        "30",
        "--max-time",
        "300",
        "-A",
        "Mozilla/5.0",
        "-o",
        str(out),
        pdf_url,
    ]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"curl failed for {pdf_url}")
    if out.stat().st_size < 1024:
        raise RuntimeError(f"downloaded file is too small: {out}")
    file_proc = subprocess.run(["file", "-b", str(out)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "PDF" not in file_proc.stdout:
        raise RuntimeError(f"downloaded file does not look like a PDF: {out} ({file_proc.stdout.strip()})")
    print(json.dumps({"pdf_url": pdf_url, "output": str(out), "bytes": out.stat().st_size}, ensure_ascii=False, indent=2))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a paper with opencli adapters and download its PDF.")
    parser.add_argument("--query", help="Paper title, arXiv ID, DOI text, or screenshot OCR text")
    parser.add_argument("--url", help="Direct paper page or PDF URL")
    parser.add_argument("--out-dir", help="Directory to save the PDF; defaults to config pdf_inbox")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--limit", type=int, default=5, help="Search result limit for title search")
    parser.add_argument("--dry-run", action="store_true", help="Resolve only; do not download")
    args = parser.parse_args()

    config = PaperNotesConfig.from_file(args.config)
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else config.pdf_inbox
    try:
        pdf_url, title, meta = resolve(args.query, args.url, args.limit)
        out = download(pdf_url, title, out_dir, args.dry_run)
        if not args.dry_run:
            meta_path = out.with_suffix(out.suffix + ".download.json")
            meta_path.write_text(
                json.dumps({"pdf_url": pdf_url, "title": title, "meta": meta}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
