# Validation Reference

Run validation before saying the workflow is complete.

## Backend Reports

When `EVIDENCE_DEEP_READ_VALIDATOR` is configured:

```bash
find "$PAPER_NOTES_ARCHIVE_ROOT" -path '*/_evidence_reports/*/report.md' | while read -r report; do
  python "$EVIDENCE_DEEP_READ_VALIDATOR" "$report"
done
```

All backend reports should pass.

## Formal Notes

Use the bundled validator:

```bash
python scripts/validate_clean_notes.py --config paper-notes.config.json
```

It checks:

- exactly 14 required second-level sections
- no old machine/report traces
- PDF embeds resolve
- Obsidian note links resolve
- figure embeds match `figure_manifest.json`
- polished notes do not retain obsolete source-PDF body lines
- no standalone single-dollar display math delimiters

## Read Markers

Check source PDFs against read markers:

```bash
pdf_dir="${PAPER_NOTES_PDF_INBOX:-./inbox/pdfs}"
comm -23 \
  <(find "$pdf_dir" -maxdepth 1 -type f -iname '*.pdf' -exec basename {} \; | sort) \
  <(find "$pdf_dir/已读标记" -maxdepth 1 -type f -name '*.已读.md' -exec basename {} .已读.md \; | sort)
```

No output means no current source PDF lacks a read marker.

## Topic Archive Refresh

After each batch is archived into `<ARCHIVE_ROOT>/<topic>/`, refresh topic inventories and family indexes with your local topic maintenance scripts. Keep those scripts outside this public repo if they contain private corpus paths or naming conventions.
