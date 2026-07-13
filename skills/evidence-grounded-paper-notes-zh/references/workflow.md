# Workflow Reference

## Pipeline

1. **Resolve from screenshot, URL, or title when needed**
   - If the user provides a screenshot, inspect it and extract the paper title, arXiv ID, DOI, venue name, URL, or PDF button text.
   - Prefer structured adapters over generic search when a matching adapter exists:

   ```bash
   opencli arxiv paper <id> -f json
   opencli arxiv search "<title>" --limit 5 -f json
   opencli brave search "<title> pdf" --limit 10 -f json
   ```

   - Use `scripts/download_paper_opencli.py` for direct URLs, arXiv IDs, and arXiv title search.
   - Save resolved PDFs into `<PDF_INBOX>`.
   - If multiple candidates are plausible, prefer exact title match, official arXiv PDF, publisher PDF, then trusted project/source repository.

2. **Discover**
   - Find source PDFs with:

   ```bash
   find "$PAPER_NOTES_PDF_INBOX" -maxdepth 1 -type f -iname '*.pdf'
   ```

   - Compare against:
     - per-topic `<ARCHIVE_ROOT>/*/pdfs`
     - archived topic notes under `<ARCHIVE_ROOT>/*/*.md`
     - `<PDF_INBOX>/已读标记/*.已读.md`
     - `论文阅读记录.md`

3. **Stage and archive**
   - For batch work, stage PDFs under a timestamped workspace in `<STAGING_ROOT>/.../pdfs/`.
   - Final canonical attachment goes into `<ARCHIVE_ROOT>/<topic>/pdfs/`.
   - Do not keep a second long-term duplicate in the reading inbox.
   - Keep `source_pdf: "pdfs/<file>.pdf"` in frontmatter.
   - Keep the Obsidian embed:

   ```md
   ## PDF 原文

   ![[pdfs/<file>.pdf]]
   ```

4. **Extract**
   - Use a local MinerU API:

   ```bash
   curl --max-time 900 -X POST "$MINERU_LOCAL_URL/file_parse" \
     -F "files=@<PDF path>" \
     -F "backend=pipeline" \
     -F "return_md=true" \
     -F "return_middle_json=true" \
     -F "return_content_list=true" \
     -o "<evidence-root>/<paper-slug>/mineru/result.json"
   ```

   - Extract `md_content` to `mineru/full_text.md`.
   - Store `content_list.json` when available.
   - Use `pdfinfo` only for metadata/page count.
   - Use plain text extraction only as an explicit fallback.

5. **Build evidence workspace**

   ```text
   <evidence-root>/<paper-slug>/
     source.pdf
     metadata.json
     mineru/
       result.json
       full_text.md
       content_list.json
     extracted/
       full_text.md
       sections.json
       figure_manifest.json
       figures/
     paper_index.json
     evidence_cards.md
     report.md
   ```

6. **Backend report**
   - Keep evidence markers and strict report sections in backend `report.md`.
   - Validate with the configured backend validator when available:

   ```bash
   python "$EVIDENCE_DEEP_READ_VALIDATOR" <archived-topic-evidence-root>/<paper-slug>/report.md
   ```

7. **Visual evidence**
   - Include meaningful MinerU `image`, `table`, and `chart` items with bbox and caption/table body.
   - Build `extracted/figure_manifest.json`:

   ```bash
   python scripts/build_figure_manifest.py --config paper-notes.config.json --crop
   ```

   - Backend `report.md` and formal Obsidian note should embed the same registered visual set.

8. **Formal note**
   - Use `references/clean-note-format.md`.
   - Keep it Chinese-first and readable.
   - Avoid exposing backend terms such as `MinerU`, `Evidence`, `Inference`, `full_text`, `paper_index`, and validator wording.
   - Final formal note lives in `<ARCHIVE_ROOT>/<topic>/`.

9. **Read marker**

   ```md
   ---
   source_pdf: "<source PDF path>"
   note: "<Obsidian note path>"
   status: 已读
   read_at: YYYY-MM-DD HH:mm
   ---

   # <PDF file name> 已读

   状态：已读
   ```

10. **Index**
   - Append to `论文阅读记录.md`:

   ```md
   1. [[笔记文件名|论文名称]]（YYYY-MM-DD，已读）— 阅读时间：YYYY-MM-DD HH:mm
   ```

11. **Topic-family follow-up**
   - If the paper belongs to an existing same-type topic, continue into the topic workflow instead of stopping at the single note.
   - Recommended follow-up:
     - copy staged PDF/evidence into `<ARCHIVE_ROOT>/<topic>/pdfs/` and `<ARCHIVE_ROOT>/<topic>/_evidence_reports/`
     - refresh topic archive index
     - refresh inventory JSON
     - refresh overview / academic / engineering surveys when the corpus is maintained that way
   - Only skip this phase when explicitly deferred.

## Important Constraints

- Do not rename source PDFs to mark reading status.
- Do not delete historical read markers unless asked.
- Create a timestamped backup before bulk rewriting top-level notes.
- Preserve user edits if they appear after a previous automated pass.
- The reading inbox should stay light; do not rebuild it into a second long-term archive of PDFs and evidence folders.
- Same-type papers are living corpora. After new papers are processed, scan for directly related notes that still live outside the topic archive and fold them in before closing the workflow.
