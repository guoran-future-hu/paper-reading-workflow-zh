import json
from pathlib import Path

from paper_notes.validate_notes import (
    REQUIRED_H2,
    frontmatter_value,
    manifest_expected_items,
    validate_figures,
    validate_pdf_links,
    validate_sections,
    validate_wiki_links,
)

FRONTMATTER = """---
title: "Sample Paper"
status: 已读
source_pdf: "pdfs/sample.pdf"
---
"""


def build_note(figure_lines: str = "") -> str:
    body = [FRONTMATTER, "# Sample Paper", ""]
    for heading in REQUIRED_H2:
        body.append(heading)
        if heading == "## PDF 原文":
            body.append("![[pdfs/sample.pdf]]")
        elif heading == "## 5. 关键图表解读" and figure_lines:
            body.append(figure_lines)
        else:
            body.append("这一节是中文正文示例。")
        body.append("")
    return "\n".join(body)


def make_vault(tmp_path: Path, note_text: str) -> Path:
    notes_dir = tmp_path / "vault"
    (notes_dir / "pdfs").mkdir(parents=True)
    (notes_dir / "pdfs" / "sample.pdf").write_bytes(b"%PDF-1.4 fake")
    (notes_dir / "sample-note.md").write_text(note_text, encoding="utf-8")
    return notes_dir


class TestSections:
    def test_valid_note_passes(self, tmp_path):
        errors: list[str] = []
        validate_sections(Path("n.md"), build_note(), errors)
        assert errors == []

    def test_missing_heading(self):
        errors: list[str] = []
        text = build_note().replace("## 10. 局限与批判", "## 10. 别的标题")
        validate_sections(Path("n.md"), text, errors)
        assert any("missing heading" in e for e in errors)

    def test_machine_trace_rejected(self):
        errors: list[str] = []
        text = build_note().replace("这一节是中文正文示例。", "MinerU 抽取结果显示……", 1)
        validate_sections(Path("n.md"), text, errors)
        assert any("trace wording" in e for e in errors)

    def test_standalone_dollar_rejected(self):
        errors: list[str] = []
        text = build_note() + "\n$\nx = 1\n$\n"
        validate_sections(Path("n.md"), text, errors)
        assert any("single-dollar" in e for e in errors)


class TestLinks:
    def test_pdf_links_ok(self, tmp_path):
        notes_dir = make_vault(tmp_path, build_note())
        errors: list[str] = []
        validate_pdf_links(notes_dir, notes_dir / "sample-note.md", build_note(), errors)
        assert errors == []

    def test_missing_source_pdf_frontmatter(self, tmp_path):
        notes_dir = make_vault(tmp_path, build_note())
        errors: list[str] = []
        text = build_note().replace('source_pdf: "pdfs/sample.pdf"\n', "")
        validate_pdf_links(notes_dir, notes_dir / "sample-note.md", text, errors)
        assert any("missing source_pdf" in e for e in errors)

    def test_broken_wiki_link(self, tmp_path):
        text = build_note() + "\n参见 [[不存在的笔记]]。\n"
        notes_dir = make_vault(tmp_path, text)
        notes = [notes_dir / "sample-note.md"]
        errors: list[str] = []
        validate_wiki_links(notes, {notes[0]: text}, errors)
        assert any("broken note link" in e for e in errors)

    def test_wiki_link_to_existing_note(self, tmp_path):
        text = build_note() + "\n参见 [[other-note|另一篇]]。\n"
        notes_dir = make_vault(tmp_path, text)
        (notes_dir / "other-note.md").write_text(build_note(), encoding="utf-8")
        notes = [notes_dir / "sample-note.md", notes_dir / "other-note.md"]
        errors: list[str] = []
        validate_wiki_links(notes, {notes[0]: text}, errors)
        assert errors == []


class TestFigures:
    def write_manifest(self, tmp_path: Path, items: list[dict]) -> Path:
        evidence_dir = tmp_path / "_evidence_reports"
        extracted = evidence_dir / "sample" / "extracted"
        extracted.mkdir(parents=True)
        (extracted / "figure_manifest.json").write_text(
            json.dumps({"items": items}), encoding="utf-8"
        )
        return evidence_dir

    def figure_line(self, n: int) -> str:
        return "\n".join(
            f"![图 {i}](_evidence_reports/sample/extracted/figures/{i:03d}-figure-{i}.png)"
            for i in range(1, n + 1)
        )

    def test_counts_match(self, tmp_path):
        evidence_dir = self.write_manifest(tmp_path, [{"id": 1}, {"id": 2}])
        text = build_note(self.figure_line(2))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("n.md"): text}, errors)
        assert errors == []

    def test_count_mismatch(self, tmp_path):
        evidence_dir = self.write_manifest(tmp_path, [{"id": 1}, {"id": 2}])
        text = build_note(self.figure_line(1))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("n.md"): text}, errors)
        assert any("manifest=2" in e for e in errors)

    def test_skip_escape_hatch(self, tmp_path):
        evidence_dir = self.write_manifest(
            tmp_path, [{"id": 1}, {"id": 2, "skip": True}]
        )
        text = build_note(self.figure_line(1))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("n.md"): text}, errors)
        assert errors == []

    def test_manifest_expected_items_shapes(self):
        assert manifest_expected_items({"items": [{}, {"skip": True}]}) == 1
        assert manifest_expected_items([{}, {}]) == 2
        assert manifest_expected_items("garbage") == 0


def test_frontmatter_value_quoted_and_bare():
    text = 'title: "A Paper"\nstatus: 已读\n'
    assert frontmatter_value(text, "title") == "A Paper"
    assert frontmatter_value(text, "status") == "已读"
    assert frontmatter_value(text, "missing") == ""
