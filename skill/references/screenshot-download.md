# Screenshot / URL / OpenCLI Download Reference

Use this reference when the user provides a screenshot of a paper page, a paper title, a DOI, an arXiv ID, or a website URL and asks to download/process the paper.

## Resolution Order

1. **Inspect screenshot**
   - Extract visible title, author names, arXiv ID, DOI, venue name, URL, or PDF button text.
   - If a local image is provided, use visual inspection/OCR from the image. Do not guess a title when text is unreadable.

2. **Use an adapter**
   - Check existing adapters with `opencli list`.
   - For arXiv:

   ```bash
   opencli arxiv paper <id> -f json
   opencli arxiv search "<paper title>" --limit 5 -f json
   ```

   If an unquoted title search returns weak or unrelated candidates, retry with the exact title wrapped in quotes before using broader search.

   - For broader web discovery:

   ```bash
   opencli brave search "<paper title> pdf" --limit 10 -f json
   ```

3. **Download**
   - Prefer official PDF links:
     - arXiv `https://arxiv.org/pdf/<id>`
     - publisher PDF link
     - official project/repository PDF
   - Use:

   ```bash
   python scripts/download_paper_opencli.py \
     --query "<title or arXiv ID>" \
     --config paper-notes.config.json
   ```

   - For direct URLs:

   ```bash
   python scripts/download_paper_opencli.py \
     --url "<paper or pdf url>" \
     --config paper-notes.config.json
   ```

4. **Verify**
   - Confirm the saved file exists, has `.pdf`, is non-empty, and `file <pdf>` identifies it as PDF.
   - If the page resolves to HTML or a login wall, use the site-specific adapter or browser workflow, then download the actual PDF.
   - After the PDF lands in `<PDF_INBOX>`, continue the normal workflow.

## Candidate Selection

Prefer candidates in this order:

1. Exact arXiv ID from screenshot or user text.
2. Exact title match from `opencli arxiv search`.
3. Exact title match from official publisher or conference page.
4. Exact title match from official project/repository.
5. Search result that clearly exposes a PDF from a trusted domain.

If more than one candidate has different titles or versions, ask the user before downloading. Do not automatically download a merely similar title.

## Adapter Role

Use adapters for page/search semantics. Use `curl` as the byte downloader after a PDF URL is known. Do not treat adapter output as trusted unless the title, identifier, and source URL agree.
