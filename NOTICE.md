# Notice and Attribution

This repository is an adapted workflow, not a claim of invention from a blank page.

The paper-reading process here was developed after studying:

- [MoonKirito/evidence-grounded-paper-deep-read](https://github.com/MoonKirito/evidence-grounded-paper-deep-read), a public paper-reading Skill released under the MIT License.

This repository then iterates that pattern for a local workflow around:

- appendix preflight before paid extraction
- Datalab PDF extraction (MinerU as an alternative backend)
- post-extraction splitting into body, references, and appendix
- clean English Obsidian notes
- visual/table manifests
- one `raw/<paper-id>/` folder per paper, plus topic archives

The workflow also depends conceptually and operationally on these projects:

- [OpenCLI](https://github.com/jackwener/OpenCLI), used as the adapter layer for paper lookup and source discovery.
- [MinerU](https://github.com/opendatalab/MinerU), used for PDF/document extraction into Markdown/JSON-style evidence.

The public version in this repository has been reorganized, generalized, and sanitized so it can be reused without exposing a private machine layout. Please respect the upstream projects' own licenses and attribution requirements when redistributing or modifying this workflow.
