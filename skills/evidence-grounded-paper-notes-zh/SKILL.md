---
name: evidence-grounded-paper-notes-zh
description: "Process research PDFs into raw per-paper evidence and English Obsidian notes. Use for paper download or extraction, appendix-aware Datalab processing, paper-note writing, or selective visual evidence."
---

# Paper Reading Notes

Default to a full-paper run. Stop early only when the user explicitly asks to resolve/download a source or rewrite an existing note.

For multiple papers, run one subagent per paper; each runs the full sequence for its own paper id only.

Run every command from the repo root as `.venv/bin/<command>`; `paper-notes.config.json` and the `DATALAB_API_KEY` in `.env` load automatically. `<P>` is the paper id `paper-notes-init` prints — every later command takes it as `--paper-dir <P>`.

## Full-Paper Run

1. **Trusted PDF and exact title.** Before resolving from a screenshot, title, URL, DOI or arXiv ID, read `references/screenshot-download.md`. Take the title from the paper or its arXiv record, never from the filename.
2. **Raw folder.** `paper-notes-init --pdf <file> --title "<exact title>" [--source-url <url>]`
   Creates `<READING_INBOX>/raw/<P>/` with `source.pdf`, `metadata.json`, `text/`, `figures/files/`. `<P>` is the title slug; a different PDF with the same title gets a hash suffix.
3. **Extract.**
   - HTML version exists (arXiv: `https://arxiv.org/html/<arxiv-id>`, or publisher HTML) → `paper-notes-extract-html --paper-dir <P> --url <url>`. Free: writes `defuddle/full_text.md`, restores the arXiv bibliography defuddle drops, saves the page's own figures as `NNN-<figure-label>-<asset>`, and builds `figures/manifest.json` with appendix figures pre-marked `skip`.
   - Exit code 2 = no HTML version → paid path: `paper-notes-extract-datalab --paper-dir <P> --mode fast`, then `paper-notes-figures --paper-dir <P>`. Datalab receives only the pages before the detected appendix; the pdftotext copy of the rest lands in `text/*-local.md`.
4. **Split.** `paper-notes-split --paper-dir <P>` → `text/pruned.md`, `references.md`, `appendix.md`, falling back to the `*-local.md` copies for any section the extraction lacks. It refuses to overwrite an already-pruned `pruned.md` without `--force`.
   Then load the `prune-paper` skill and do its Phase 2–3 review and noise pruning on `text/pruned.md`.
5. **Choose visuals.** `paper-notes-select --paper-dir <P>` lists the candidates. Keep only visuals that materially support the method, architecture, ablations or main results; appendix visuals stay skipped by default; zero is valid. Record the choice: `paper-notes-select --paper-dir <P> --id 1 --id 4 ...` (`--skip N` / `--unskip N` adjust single items).
6. **Scaffold.** `paper-notes-scaffold --paper-dir <P> --authors "..." --year YYYY [--tag <ascii-tag> ...]` writes `<READING_INBOX>/<P>.md`: frontmatter, the PDF embed, the body sections from the `paper-summarizer` skill's Output block with its guidance as `<!-- TODO -->` markers, and a closing TODO block listing the chosen visuals to place.
   Choose visuals before scaffolding. Changing the choice later means adding or removing embeds by hand until the note embeds exactly the selected, unskipped items — the validator counts them.
7. **Write the note.** Load the `paper-summarizer` skill and write the body by it from `text/pruned.md` (plus `appendix.md` where it matters), replacing every `<!-- TODO -->` marker. That skill owns the sections and the writing; the rules below cover only what the pipeline needs.
8. **Index.** `paper-notes-index --paper-id <P> --topic "<short label>"` adds or updates the paper's row in `<READING_INBOX>/reading-index.md`, the only reading index.
9. **Validate.** Read `references/validation.md`, then run `paper-notes-validate`. Done means it prints `clean notes validation: ok`.

## Pipeline Rules for the Note

- English throughout. Display title/authors may be Unicode; filenames, paths, ids, YAML keys, tags and status stay ASCII.
- Keep the frontmatter and `## PDF Source` as scaffolded.
- Link other notes as `[[<paper-id>]]`, only notes that exist in `<READING_INBOX>`.
- The user's own notes on a paper sit beside it as `<paper-id>.<kind>.md` (e.g. `.critique.md`). They are his: the pipeline never writes, rewrites or validates them.

## Figures

Figures have no section of their own. Place each chosen figure in whichever section it helps explain — an architecture diagram in the method, a results plot beside the results — then delete the scaffold's figure block. Every chosen figure is placed exactly once.

Under each embed, one paragraph: **Fig. N — a short title of your own.** What the figure shows — which panel, row or curve is which, which model or setting produces what — then `Takeaway:` the one thing it establishes for the paper's argument.

- Look at the image itself (`vision_analyze` on `raw/<P>/figures/files/<file>`) to see its layout and what it compares, and read it together with the paper's text that discusses it.
- Numbers, labels and claims come from the paper's text and caption; image reading misreads small print.
- Say what the reader would otherwise need to squint at the figure to get. Restating the caption is not an explanation.
