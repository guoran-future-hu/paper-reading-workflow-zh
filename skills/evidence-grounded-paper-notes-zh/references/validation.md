# Validation Reference

```bash
.venv/bin/paper-notes-validate
```

Validates every note in `<READING_INBOX>` against the `raw/` folder beside it. A failure line names the note and the rule; fix the note (or the manifest selection) and re-run until it prints `clean notes validation: ok`.

It checks:

- a `## PDF Source` section, at least one body section, no empty section, and no `<!-- TODO` marker left — which sections exist is the `paper-summarizer` skill's call, not the validator's
- `paper_id`, `status`, `source_pdf` and the note filename are ASCII
- the PDF embed and `source_pdf` resolve
- `[[note]]` links point at existing notes
- the note embeds exactly the manifest items that are `selected` and not `skip`
- the note's `raw/<paper-id>/` holds `metadata.json` and `text/pruned.md`, `references.md`, `appendix.md`
- the note has a row in `reading-index.md`
- no standalone single-`$` display-math line

Tests: run `pytest`; never issue paid Datalab requests from a test.
