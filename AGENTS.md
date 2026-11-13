# AGENTS.md

This is a paper reading pipeline that also maintains a research knowledge base. The directory is shared across platforms — mainly Windows and Linux — by Syncthing, so keep paths relative and slashes forward in anything that ships.

Every instruction an agent needs lives under `skills/`, chiefly `skills/evidence-grounded-paper-notes-zh`. Load it when the user says "run this paper", "process the paper", "论文阅读".

This is a local fork, no longer synced from `LeoLin990405/paper-reading-workflow-zh`. Change code, skills and docs freely to fit the user's needs; keep the tests passing.

Where things actually live is defined in code, not prose:

- `paper_notes/config.py` — `PaperNotesConfig`, every path and default
- `paper-notes.config.json` — machine-local override, gitignored
- `skills/*/references/` — procedures that are too long to inline

Windows-only aside: a second, unrelated skill collection sits at `D:\agents-hub-skill-backup` on the Windows machine. Nothing in this repository depends on it.
