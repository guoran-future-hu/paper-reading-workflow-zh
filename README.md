<div align="center">

[![English](https://img.shields.io/badge/Language-English-2ea44f?style=for-the-badge)](README.md) &nbsp; [![中文](https://img.shields.io/badge/语言-中文-555555?style=for-the-badge)](README.zh-CN.md)

# Paper Reading Workflow ZH

### Local-first evidence workflows for Chinese paper notes, topic archives, and surveys

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Local%20First-black?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Language-Python-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Workflow-Skills%20%2B%20Obsidian-purple?style=for-the-badge" />
  <a href="https://github.com/LeoLin990405/paper-reading-workflow-zh/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/LeoLin990405/paper-reading-workflow-zh/ci.yml?branch=main&style=for-the-badge&label=CI" /></a>
  <img src="https://img.shields.io/badge/License-MIT-yellowgreen?style=for-the-badge" />
</p>

</div>

> Turn scattered PDFs into a living Chinese research corpus: source files, extraction evidence, readable Obsidian notes, topic archives, and overview / academic / engineering surveys stay connected.

---

## Overview

Paper Reading Workflow ZH packages a local paper-reading practice into reusable Codex Skills and Python helpers. It is designed for readers who do not want a disposable summary: every processed paper keeps a backend evidence workspace, a clean Chinese Obsidian note, and a path into a topic-level archive.

The workflow is intentionally split into two levels:

- **Single paper:** download or register a PDF, extract text and visuals, keep evidence artifacts, write a 14-section Chinese note, mark it as read.
- **Topic corpus:** fold same-type papers into a topic archive, maintain an inventory, and refresh overview, academic, and engineering surveys.

Private paths and local service addresses are kept out of the repository. Real locations live in environment variables or `paper-notes.config.json`, which is ignored by git.

## 1. What It Handles

| Layer | Output | Purpose |
|---|---|---|
| Paper inbox | PDFs and read markers | Keep source files and reading status explicit |
| Evidence workspace | MinerU JSON/Markdown, figures, manifests, reports | Preserve extraction and claim-level grounding |
| Formal note | 14-section Chinese Obsidian note | Make the paper readable and reviewable |
| Topic archive | Notes, PDFs, `_evidence_reports`, index, inventory | Treat same-type papers as a corpus |
| Topic surveys | `全景综述`, `学术综述`, `工程综述` | Turn a corpus into reusable synthesis |

## 2. Workflow Map

![Paper Reading Workflow ZH pipeline](images/workflow-en.svg)

```text
paper title / URL / PDF
  -> OpenCLI-assisted discovery
  -> PDF inbox
  -> MinerU extraction
  -> evidence workspace
  -> visual manifest
  -> clean Chinese Obsidian note
  -> read marker + reading index
  -> topic archive
  -> overview / academic / engineering surveys
  -> recurring maintenance
```

All Skills live in `skills/`. The single-paper Skill is `skills/evidence-grounded-paper-notes-zh/`; the topic-family Skills sit next to it.

## 3. Repository Layout

```text
.
├── skills/
│   ├── evidence-grounded-paper-notes-zh/
│   ├── paper-knowledge-family-zh/
│   ├── paper-topic-archive-zh/
│   ├── paper-topic-survey-zh/
│   └── paper-topic-maintenance-zh/
├── paper_notes/
│   ├── config.py
│   ├── download.py
│   ├── mineru_extract.py
│   ├── figure_manifest.py
│   └── validate_notes.py
├── scripts/            # thin wrappers around paper_notes modules
├── tests/
├── examples/
│   ├── paper-notes.config.example.json
│   ├── read-marker.example.md
│   └── sample-vault/   # runnable demo vault for the validator
├── images/
├── NOTICE.md
└── README.zh-CN.md
```

## 4. Requirements

- Python 3.10+
- `curl`
- [OpenCLI](https://github.com/jackwener/OpenCLI), optional but recommended for paper discovery
- A local [MinerU](https://github.com/opendatalab/MinerU) API for PDF extraction
- Poppler `pdftoppm` and `Pillow` only when cropping visual evidence:

```bash
python -m pip install ".[visual]"
```

## 5. Quick Start

Clone and install locally:

```bash
git clone https://github.com/LeoLin990405/paper-reading-workflow-zh.git
cd paper-reading-workflow-zh
python -m pip install -e .
```

Installing exposes `paper-notes-download`, `paper-notes-extract`, `paper-notes-figures`, and `paper-notes-validate` as commands. The `python scripts/*.py` forms below also work straight from a clone without installing.

Try the validator on the bundled sample vault (no MinerU or OpenCLI needed):

```bash
paper-notes-validate --notes-dir "examples/sample-vault/注意力机制"
```

Create a private config:

```bash
cp examples/paper-notes.config.example.json paper-notes.config.json
```

Download or register a paper:

```bash
python scripts/download_paper_opencli.py \
  --query "Attention Is All You Need" \
  --config paper-notes.config.json
```

Extract PDFs with MinerU:

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

## 6. Configuration

Use `paper-notes.config.json`, or set environment variables:

```bash
export PAPER_NOTES_PDF_INBOX="$HOME/Papers/inbox"
export PAPER_NOTES_READING_INBOX="$HOME/Documents/Obsidian/ResearchVault/论文阅读"
export PAPER_NOTES_ARCHIVE_ROOT="$HOME/Documents/Obsidian/ResearchVault/论文笔记"
export PAPER_NOTES_STAGING_ROOT="$HOME/Archives/paper-reading-workflow"
export MINERU_LOCAL_URL="http://127.0.0.1:8010"
```

`examples/paper-notes.config.example.json` documents the same fields. Keep the real config local.

## 7. Skill Family

| Skill | Role |
|---|---|
| `evidence-grounded-paper-notes-zh` | Single-paper download, extraction, note writing, read markers |
| `paper-knowledge-family-zh` | Orchestrates the whole paper knowledge family |
| `paper-topic-archive-zh` | Folds same-type notes into topic archives |
| `paper-topic-survey-zh` | Maintains `全景综述`, `学术综述`, and `工程综述` |
| `paper-topic-maintenance-zh` | Keeps living corpora current after new papers arrive |

The core rule is:

```text
single-paper note -> topic archive -> survey refresh -> recurring maintenance
```

## 8. Note Contract

Formal Obsidian notes use a fixed 14-section structure:

```text
PDF 原文
已读信息
1. 一句话总览
2. 论文基本信息
3. 研究问题
4. 核心方法
5. 关键图表解读
6. 实验与结果
7. 公式与技术细节
8. 核心概念解释
9. 创新点与深度理解
10. 局限与批判
11. 和已读论文的关系
12. 对我的启发
```

Backend terms such as `Evidence`, `Inference`, `MinerU`, `full_text`, `paper_index`, and `evidence_cards` should stay out of the polished note body.

## 9. Development

```bash
python -m pip install -e ".[dev]"
ruff check paper_notes scripts tests
pytest
```

CI runs lint, unit tests, and a validation pass over `examples/sample-vault/` on Python 3.10 and 3.12.

## 10. Attribution

This project was iterated after studying [MoonKirito/evidence-grounded-paper-deep-read](https://github.com/MoonKirito/evidence-grounded-paper-deep-read), a paper-reading Skill released under the MIT License.

Thanks also to [OpenCLI](https://github.com/jackwener/OpenCLI) for adapter-style paper discovery and [MinerU](https://github.com/opendatalab/MinerU) for document-to-Markdown/JSON extraction.

See `NOTICE.md` for attribution details.

## 11. License

MIT. See `LICENSE`.
