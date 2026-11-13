# Notice and Attribution

This repository is a fork of [LeoLin990405/paper-reading-workflow-zh](https://github.com/LeoLin990405/paper-reading-workflow-zh) (MIT), which was itself developed after studying [MoonKirito/evidence-grounded-paper-deep-read](https://github.com/MoonKirito/evidence-grounded-paper-deep-read) (MIT). The fork has since diverged: the topic-archive and survey skills, the MinerU backend and the fixed 15-section note format were removed, and the pipeline was rebuilt as per-step scripts.

It relies on:

- [Datalab](https://www.datalab.to/) for paid PDF-to-Markdown extraction
- [defuddle](https://github.com/kepano/defuddle) for free extraction of HTML paper versions
- [OpenCLI](https://github.com/jackwener/OpenCLI) for arXiv lookup
- Poppler's `pdftotext` for the appendix preflight

Please respect those projects' own licenses when redistributing or modifying this workflow.
