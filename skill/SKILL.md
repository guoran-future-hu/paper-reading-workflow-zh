---
name: evidence-grounded-paper-notes-zh
description: "End-to-end Chinese evidence-grounded paper reading workflow for PDFs, MinerU extraction, Obsidian notes, visual evidence manifests, read markers, and topic archive maintenance."
---

# Evidence-Grounded Paper Notes ZH

## Core Contract

Produce two separate layers:

1. **Backend evidence layer**
   - A temporary staging evidence workspace may live under `<STAGING_ROOT>/.../_evidence_reports/<paper-slug>/`.
   - After archival, the canonical evidence layer should live under `<ARCHIVE_ROOT>/<topic>/_evidence_reports/<paper-slug>/`.
   - Use MinerU output, evidence cards, figure manifests, cropped figures, and `report.md`.
   - Keep this layer strict and validator-friendly.
2. **Frontend Obsidian formal note**
   - Final notes should live under `<ARCHIVE_ROOT>/<topic>/<paper-note>.md`.
   - Make the note clean, Chinese-first, readable, and reviewable.
   - Do not expose extraction or validator process traces in the formal note.
   - Do not concatenate the backend report and an old note into a duplicated double structure.
   - Preserve source provenance in frontmatter, read markers, and archive manifests.

`<READING_INBOX>` is a light operational inbox. Use it mainly for `论文阅读记录.md` and temporary staging needs, not as the long-term home of finished formal notes.

## Configuration

Use `examples/paper-notes.config.example.json` as the local template, or set environment variables:

- `PAPER_NOTES_PDF_INBOX`
- `PAPER_NOTES_READING_INBOX`
- `PAPER_NOTES_ARCHIVE_ROOT`
- `PAPER_NOTES_STAGING_ROOT`
- `MINERU_LOCAL_URL`
- `EVIDENCE_DEEP_READ_VALIDATOR`

Default script paths are intentionally local and safe:

- PDF inbox: `./inbox/pdfs`
- Reading inbox: `./vault/论文阅读`
- Archive root: `./vault/论文笔记`
- Staging root: `./workspace/staging`
- MinerU local API: `http://127.0.0.1:8010/file_parse`

Read `references/workflow.md` before processing papers. Read `references/screenshot-download.md` before downloading papers from screenshots, URLs, titles, or adapter output. Read `references/clean-note-format.md` before writing or rewriting formal Obsidian notes.

## Workflow

1. If the request starts from a screenshot, URL, title, or search result, resolve and download the PDF first.
   - Extract the paper title, arXiv ID, DOI, venue page, or URL.
   - Prefer structured adapters such as `opencli arxiv` before broad web search.
   - Save downloaded PDFs into `<PDF_INBOX>` with stable, readable file names.
   - Use `scripts/download_paper_opencli.py` for direct URLs, arXiv IDs, and arXiv title search.
2. Discover new PDFs.
   - Compare source PDFs with per-topic `pdfs/`, archived notes, the reading index, and `已读标记/*.已读.md`.
   - Treat a source PDF as handled only when attachment, note, index entry, and read marker all exist.
3. Stage each new PDF for archival.
   - Final canonical attachment goes to `<ARCHIVE_ROOT>/<topic>/pdfs/` without renaming it.
4. Extract each source PDF with MinerU local API.
   - Use `scripts/mineru_local_batch_extract.py`.
   - Confirm API availability before a large run.
5. Build or refresh the backend evidence layer.
   - Required files include `source.pdf`, `metadata.json`, `mineru/result.json`, `mineru/full_text.md`, `paper_index.json`, `evidence_cards.md`, `report.md`, `extracted/full_text.md`, `extracted/sections.json`, `extracted/figure_manifest.json`, and `extracted/figures/`.
6. Apply visual alignment.
   - Register meaningful MinerU `image`, `table`, and `chart` items with caption/body and bbox.
   - Use `scripts/build_figure_manifest.py` to create `extracted/figure_manifest.json`.
   - If `--crop` is enabled, crop visuals from `source.pdf` into `extracted/figures/`.
   - Embed the registered visual set in both backend `report.md` and formal Obsidian note.
7. Write the formal Obsidian note in the clean Chinese format.
   - Use exactly the 14 second-level sections in `references/clean-note-format.md`.
   - Preserve frontmatter, H1 original title, PDF embed, and read status.
   - Prefer Chinese prose. Keep English only where it preserves original technical meaning.
   - Final formal note goes to `<ARCHIVE_ROOT>/<topic>/`, not the long-term inbox.
   - Write long notes incrementally or through file-based scripts. Avoid one giant prompt/tool-call body for a full note.
8. Create read markers in `<PDF_INBOX>/已读标记`.
   - File name: `<PDF original file name>.已读.md`
   - Include `source_pdf`, `note`, `status: 已读`, and `read_at`.
9. Update `论文阅读记录.md`.
   - Format: `1. [[笔记文件名|论文名称]]（YYYY-MM-DD，已读）— 阅读时间：YYYY-MM-DD HH:mm`
10. Validate before reporting completion.
   - Run backend report validation when a backend validator is configured.
   - Run `scripts/validate_clean_notes.py`.
   - Confirm PDF embeds, note links, figure counts, read markers, and machine-trace cleanup.
11. If the paper belongs to an existing same-type topic corpus, continue into topic-family maintenance.
   - Refresh topic index/inventory and survey files.
   - Treat the topic archive as a living corpus unless the user explicitly defers maintenance.

## Bundled Scripts

- `scripts/download_paper_opencli.py`: resolve arXiv IDs/titles/direct URLs with opencli and download PDFs.
- `scripts/mineru_local_batch_extract.py`: batch MinerU extraction for the configured PDF inbox and evidence workspace.
- `scripts/build_figure_manifest.py`: build a figure/table/chart manifest from MinerU output, optionally cropping images.
- `scripts/validate_clean_notes.py`: validate formal clean-note structure and consistency with figure manifests.

## Completion Criteria

Report completion only when all relevant items are true:

- No unprocessed source PDF remains unless it is intentionally skipped and documented.
- Screenshot/URL/title requests either produce a downloaded PDF or clearly document why no trusted PDF link could be resolved.
- Every processed PDF has an Obsidian PDF attachment, formal note, index entry, and source read marker.
- Every processed formal note lives in a topic archive, not as an unarchived long-term inbox note.
- Every backend `report.md` passes the configured backend validator.
- Every formal note has the clean 14-section structure.
- Formal notes do not retain obsolete source-file lines in the polished body.
- Formal notes have no backend trace terms such as `Evidence`, `Inference`, `MinerU`, `full_text`, `paper_index`, or `evidence_cards`.
- Formal note figure embed counts match `extracted/figure_manifest.json`.
- PDF embeds and Obsidian note links resolve.
- If the processed paper belongs to an active same-type topic corpus, the topic-family follow-up has either been executed or explicitly deferred.
