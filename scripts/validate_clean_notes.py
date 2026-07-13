#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from paper_notes.config import PaperNotesConfig
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from paper_notes.config import PaperNotesConfig


REQUIRED_H2 = [
    "## PDF 原文",
    "## 已读信息",
    "## 1. 一句话总览",
    "## 2. 论文基本信息",
    "## 3. 研究问题",
    "## 4. 核心方法",
    "## 5. 关键图表解读",
    "## 6. 实验与结果",
    "## 7. 公式与技术细节",
    "## 8. 核心概念解释",
    "## 9. 创新点与深度理解",
    "## 10. 局限与批判",
    "## 11. 和已读论文的关系",
    "## 12. 对我的启发",
]

MACHINE_TRACE = re.compile(
    r"\b(Evidence:|Inference from|Not clearly stated|MinerU|full_text|paper_index|"
    r"evidence_cards|报告语言|证据锚点|完整性自检|作者做了什么|作者为什么|"
    r"作者具体怎么做|作者如何验证)\b"
)


def fail(errors: list[str]) -> int:
    if errors:
        print("\n".join(errors))
        return 1
    print("clean notes validation: ok")
    return 0


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf'^{re.escape(key)}:\s*"(.+?)"\s*$', text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def note_files(notes_dir: Path, index_name: str) -> list[Path]:
    return sorted(p for p in notes_dir.glob("*.md") if p.name != index_name)


def validate_sections(path: Path, text: str, errors: list[str]) -> None:
    h2_count = len(re.findall(r"^## ", text, flags=re.MULTILINE))
    if h2_count != len(REQUIRED_H2):
        errors.append(f"{path.name}: expected {len(REQUIRED_H2)} H2 sections, got {h2_count}")
    for heading in REQUIRED_H2:
        if heading not in text:
            errors.append(f"{path.name}: missing heading {heading}")
    if MACHINE_TRACE.search(text):
        errors.append(f"{path.name}: contains backend/report trace wording")
    if re.search(r"^\$$", text, flags=re.MULTILINE):
        errors.append(f"{path.name}: contains standalone single-dollar math delimiter")


def validate_pdf_links(notes_dir: Path, path: Path, text: str, errors: list[str]) -> None:
    source_pdf = frontmatter_value(text, "source_pdf")
    if not source_pdf:
        errors.append(f"{path.name}: missing source_pdf frontmatter")
    elif not (notes_dir / source_pdf).exists():
        errors.append(f"{path.name}: source_pdf does not exist: {source_pdf}")
    for target in re.findall(r"\[\[(pdfs/[^]|]+)(?:\|[^]]*)?\]\]", text):
        if not (notes_dir / target).exists():
            errors.append(f"{path.name}: missing PDF embed target {target}")


def validate_wiki_links(notes: list[Path], texts: dict[Path, str], errors: list[str]) -> None:
    note_stems = {p.stem for p in notes}
    for path, text in texts.items():
        for match in re.finditer(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|[^]]*)?\]\]", text):
            target = match.group(1)
            if target.startswith("pdfs/"):
                continue
            if target not in note_stems:
                errors.append(f"{path.name}: broken note link [[{target}]]")


def validate_figures(evidence_dir: Path, texts: dict[Path, str], errors: list[str]) -> None:
    if not evidence_dir.exists():
        return
    for paper_dir in sorted(p for p in evidence_dir.iterdir() if p.is_dir()):
        manifest = paper_dir / "extracted" / "figure_manifest.json"
        if not manifest.exists():
            continue
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            items = raw.get("items", []) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
            expected = len(items)
        except json.JSONDecodeError as exc:
            errors.append(f"{paper_dir.name}: invalid figure_manifest.json: {exc}")
            continue
        pattern = f"_evidence_reports/{paper_dir.name}/extracted/figures/"
        matches = [(path.name, text.count(pattern)) for path, text in texts.items() if pattern in text]
        if expected and (len(matches) != 1 or matches[0][1] != expected):
            errors.append(f"{paper_dir.name}: manifest={expected}, note figure matches={matches}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate clean Chinese Obsidian paper notes.")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument("--notes-dir", help="Directory containing formal paper notes")
    parser.add_argument("--evidence-dir", help="Evidence report root; defaults to notes-dir/_evidence_reports")
    parser.add_argument("--index-name", default="论文阅读记录.md", help="Reading index file name to ignore")
    args = parser.parse_args()

    config = PaperNotesConfig.from_file(args.config)
    notes_dir = Path(args.notes_dir).expanduser().resolve() if args.notes_dir else config.reading_inbox
    evidence_dir = Path(args.evidence_dir).expanduser().resolve() if args.evidence_dir else notes_dir / "_evidence_reports"

    errors: list[str] = []
    if not notes_dir.exists():
        errors.append(f"notes directory does not exist: {notes_dir}")
        return fail(errors)
    notes = note_files(notes_dir, args.index_name)
    texts = {path: path.read_text(encoding="utf-8") for path in notes}
    for path, text in texts.items():
        validate_sections(path, text, errors)
        validate_pdf_links(notes_dir, path, text, errors)
    validate_wiki_links(notes, texts, errors)
    validate_figures(evidence_dir, texts, errors)
    return fail(errors)


if __name__ == "__main__":
    raise SystemExit(main())
