# Getting a Trusted PDF

Use when the user hands over a screenshot, title, arXiv ID, DOI or URL instead of a local PDF.

## Steps

1. **Read the identifier.** From a screenshot, take the visible title, authors, arXiv ID, DOI or URL; an unreadable title is asked about, not guessed.
2. **Resolve and download** with `.venv/bin/paper-notes-download`:
   - arXiv ID or exact title → `--query "<id or title>"`. It looks the paper up through `opencli arxiv`, accepts only a near-exact title match, and otherwise exits listing the candidates.
   - Any other page or PDF link → `--url "<url>"`; arXiv `abs/` links are turned into the PDF link.
   - `--dry-run` prints the resolved PDF URL and target path without downloading.
   The PDF lands in `inbox/pdfs/`, named after the title; the command itself checks it is a real, non-trivial PDF.
3. **Get the record** for the next steps: `opencli arxiv paper <id>` prints the exact title, full author list and date as JSON (`data[0]`). Feed the title to `paper-notes-init --title` and authors/year to `paper-notes-scaffold`.
4. Continue with step 2 of the main skill (`paper-notes-init`).

## Choosing a candidate

Prefer, in order: the exact arXiv ID the user gave; an exact title match on arXiv; the publisher's or conference's own PDF; the authors' project page. When candidates differ in title or version, ask the user. A merely similar title is never downloaded.

## Not on arXiv

Find the publisher or project page (web search, or `opencli` for sites it has adapters for — `opencli list`), then `--url` the PDF link. A login wall or paywall goes to the `blocked-page-recovery` skill.
