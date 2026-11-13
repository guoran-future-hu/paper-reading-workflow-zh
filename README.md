# paper-reading-workflow-zh

Turns one research paper into an evidence folder and an Obsidian note that replaces a first read of the paper.

A fork of [LeoLin990405/paper-reading-workflow-zh](https://github.com/LeoLin990405/paper-reading-workflow-zh), developed independently: local is canonical, upstream is not merged. The repo name is kept from the fork; notes are written in English.

## How it works

Each step is a script; judgment (choosing figures, writing the note) is left to an agent. The procedure an agent follows is [`skills/evidence-grounded-paper-notes-zh/SKILL.md`](skills/evidence-grounded-paper-notes-zh/SKILL.md) — that file, not this README, is the reference for commands and their order.

```text
arXiv ID / title / URL ─ paper-notes-download ──► inbox/pdfs/<title>.pdf
                         paper-notes-init ──────► vault/reading/raw/<paper-id>/
  arXiv HTML (free)  ─── paper-notes-extract-html
  or PDF (Datalab)   ─── paper-notes-extract-datalab + paper-notes-figures
                         paper-notes-split ─────► text/pruned.md · references.md · appendix.md
                         paper-notes-select ────► figures/manifest.json (chosen figures)
                         paper-notes-scaffold ──► vault/reading/<paper-id>.md skeleton
                         agent writes the note
                         paper-notes-index ─────► vault/reading/reading-index.md
                         paper-notes-validate
```

- The paper id is the ASCII slug of the full title.
- The paid Datalab path sends only the pages before the detected appendix; a free `pdftotext` copy of the rest is kept.
- The note's sections come from the `paper-summarizer` skill's Output block, so the note format changes by editing that skill.
- Figures are embedded where they help explain, each with a short explanation; the validator checks every chosen figure is embedded exactly once.

## Layout

```text
vault/reading/
  <paper-id>.md            the note
  reading-index.md         the one reading index
  raw/<paper-id>/
    source.pdf  metadata.json
    defuddle/ or datalab/  extraction output
    text/                  pruned.md, references.md, appendix.md (+ *-local.md preflight copies)
    figures/               manifest.json, files/
```

`vault/`, `inbox/`, `paper-notes.config.json` and `.env` are local data and stay out of git.

## Setup

```bash
uv sync --extra dev            # or: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp examples/paper-notes.config.example.json paper-notes.config.json
echo 'DATALAB_API_KEY=...' > .env   # only needed for the paid PDF path
.venv/bin/pytest -q
```

External tools: [`defuddle`](https://github.com/kepano/defuddle) (HTML path), [`opencli`](https://github.com/jackwener/OpenCLI) (arXiv lookup), `pdftotext` (poppler), and the `prune-paper` and `paper-summarizer` agent skills.

## License

MIT. Attribution in [NOTICE.md](NOTICE.md).
