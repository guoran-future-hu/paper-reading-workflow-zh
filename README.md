<div align="center">

[![English](https://img.shields.io/badge/Language-English-2ea44f?style=for-the-badge)](README.md) &nbsp; [![中文](https://img.shields.io/badge/语言-中文-555555?style=for-the-badge)](README.zh-CN.md)

# Paper Reading Workflow ZH

### Evidence-grounded Chinese paper notes for PDFs, MinerU, and Obsidian

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Local%20First-black?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Language-Python-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Notes-Obsidian-purple?style=for-the-badge" />
  <a href="https://github.com/LeoLin990405/paper-reading-workflow-zh/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/LeoLin990405/paper-reading-workflow-zh/ci.yml?branch=main&style=for-the-badge&label=CI" /></a>
  <img src="https://img.shields.io/badge/License-MIT-yellowgreen?style=for-the-badge" />
</p>

</div>

> A reusable version of my local paper-reading process: download PDFs, extract them with MinerU, keep a strict evidence layer, and write clean Chinese Obsidian notes that remain readable after the automation is gone.

---

## Overview

This repository packages an evidence-grounded Chinese paper-reading workflow as a portable Skill plus helper scripts. It is built around a two-layer contract:

1. a backend evidence workspace with MinerU extraction, manifests, figures, evidence cards, and strict reports
2. a frontend Obsidian note with a clean 14-section Chinese reading format

The public version is sanitized: local machine paths, private vault names, and internal service addresses are replaced by environment variables and example config.

## 1. Features

- Resolve and download papers from arXiv IDs, URLs, or titles with `opencli`
- Batch extract PDFs through a local MinerU API
- Generate figure/table/chart manifests from MinerU output
- Validate clean Chinese Obsidian notes against a fixed 14-section format
- Track read markers and reading indexes
- Keep topic archives separate from temporary reading inboxes

## 2. Repository Layout

```text
.
├── skill/
│   ├── SKILL.md
│   └── references/
├── scripts/
│   ├── download_paper_opencli.py
│   ├── mineru_local_batch_extract.py
│   ├── build_figure_manifest.py
│   └── validate_clean_notes.py
├── paper_notes/
│   └── config.py
├── examples/
│   ├── paper-notes.config.example.json
│   └── read-marker.example.md
├── NOTICE.md
└── README.zh-CN.md
```

## 3. Requirements

- Python 3.10+
- `curl`
- `opencli` for paper resolution, optional but recommended
- A local MinerU API for PDF extraction
- Poppler `pdftoppm` and `Pillow` only when using visual cropping:

```bash
python -m pip install ".[visual]"
```

## 4. Quick Start

Copy and edit the example config:

```bash
cp examples/paper-notes.config.example.json paper-notes.config.json
```

Download a paper:

```bash
python scripts/download_paper_opencli.py \
  --query "Attention Is All You Need" \
  --config paper-notes.config.json
```

Extract PDFs through MinerU:

```bash
python scripts/mineru_local_batch_extract.py --config paper-notes.config.json
```

Build visual manifests:

```bash
python scripts/build_figure_manifest.py --config paper-notes.config.json
```

Validate formal notes:

```bash
python scripts/validate_clean_notes.py --config paper-notes.config.json
```

## 5. Workflow Contract

The Skill in `skill/SKILL.md` defines the working contract:

- source PDFs start in a configured inbox
- extracted evidence lives in `_evidence_reports/<paper-slug>/`
- final PDFs and notes live under a topic archive
- the formal note uses exactly 14 second-level sections
- backend extraction traces must not leak into polished notes
- figures/tables/charts should be registered in `figure_manifest.json`

See `skill/references/workflow.md` and `skill/references/clean-note-format.md` for the full specification.

## 6. Configuration

Use `paper-notes.config.json`, or set environment variables:

```bash
export PAPER_NOTES_PDF_INBOX="$HOME/Papers/inbox"
export PAPER_NOTES_READING_INBOX="$HOME/Documents/Obsidian/ResearchVault/论文阅读"
export PAPER_NOTES_ARCHIVE_ROOT="$HOME/Documents/Obsidian/ResearchVault/论文笔记"
export PAPER_NOTES_STAGING_ROOT="$HOME/Archives/paper-reading-workflow"
export MINERU_LOCAL_URL="http://127.0.0.1:8010"
```

`paper-notes.config.json` is ignored by git so private paths stay local.

## 7. Acknowledgements

This project explicitly acknowledges that it was iterated from another author's paper-reading Skill design. I studied that Skill pattern and then adapted the workflow for Chinese Obsidian notes, MinerU extraction, evidence workspaces, visual manifests, read markers, and topic-level archives.

The public repo is a generalized and sanitized derivative workflow. If you know the exact upstream Skill and license, keep its author, link, and license terms in `NOTICE.md`.

## 8. License

MIT. See `LICENSE`.
