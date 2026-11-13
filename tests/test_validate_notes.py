import json
from pathlib import Path

from paper_notes.validate_notes import (
    frontmatter_value,
    manifest_expected_items,
    validate_ascii_machine_fields,
    validate_figures,
    validate_pdf_links,
    validate_sections,
    validate_wiki_links,
)

FRONTMATTER = """---
title: "Sample Paper"
paper_id: "sample-2026"
status: read
source_pdf: "raw/sample/source.pdf"
---
"""

FILLER = "This section holds English prose for the sample note."
HEADINGS = ["## PDF Source", "## 1. Abstract", "## 3. How It Works", "## 5. Results"]


def build_note(figure_lines: str = "") -> str:
    body = [FRONTMATTER, "# Sample Paper", ""]
    for heading in HEADINGS:
        body.append(heading)
        if heading == "## PDF Source":
            body.append("![[raw/sample/source.pdf]]")
        elif heading == "## 5. Results" and figure_lines:
            body.append(figure_lines)
        else:
            body.append(FILLER)
        body.append("")
    return "\n".join(body)


def make_vault(tmp_path: Path, note_text: str) -> Path:
    notes_dir = tmp_path / "vault"
    (notes_dir / "raw" / "sample").mkdir(parents=True)
    (notes_dir / "raw" / "sample" / "source.pdf").write_bytes(b"%PDF-1.4 fake")
    (notes_dir / "sample-2026.md").write_text(note_text, encoding="utf-8")
    return notes_dir


class TestSections:
    def test_valid_note_passes(self, tmp_path):
        errors: list[str] = []
        validate_sections(Path("sample-2026.md"), build_note(), errors)
        assert errors == []

    def test_missing_pdf_section(self):
        errors: list[str] = []
        text = build_note().replace("## PDF Source", "## Source")
        validate_sections(Path("sample-2026.md"), text, errors)
        assert any("missing heading ## PDF Source" in e for e in errors)

    def test_any_body_headings_accepted(self):
        errors: list[str] = []
        text = build_note().replace("## 3. How It Works", "## 3. Taxonomy") + "\n## Appendix\nnotes\n"
        validate_sections(Path("sample-2026.md"), text, errors)
        assert errors == []

    def test_empty_section_rejected(self):
        errors: list[str] = []
        text = build_note().replace("## 5. Results\n" + FILLER, "## 5. Results\n")
        validate_sections(Path("sample-2026.md"), text, errors)
        assert any("empty section ## 5. Results" in e for e in errors)

    def test_standalone_dollar_rejected(self):
        errors: list[str] = []
        text = build_note() + "\n$\nx = 1\n$\n"
        validate_sections(Path("sample-2026.md"), text, errors)
        assert any("single-dollar" in e for e in errors)


class TestAsciiFields:
    def test_ascii_note_passes(self):
        errors: list[str] = []
        validate_ascii_machine_fields(Path("sample-2026.md"), build_note(), errors)
        assert errors == []

    def test_non_ascii_paper_id_rejected(self):
        errors: list[str] = []
        text = build_note().replace('paper_id: "sample-2026"', 'paper_id: "样本-2026"')
        validate_ascii_machine_fields(Path("sample-2026.md"), text, errors)
        assert any("paper_id must be ASCII" in e for e in errors)

    def test_non_ascii_status_rejected(self):
        errors: list[str] = []
        text = build_note().replace("status: read", "status: 已读")
        validate_ascii_machine_fields(Path("sample-2026.md"), text, errors)
        assert any("status must be ASCII" in e for e in errors)

    def test_non_ascii_filename_rejected(self):
        errors: list[str] = []
        validate_ascii_machine_fields(Path("样本笔记.md"), build_note(), errors)
        assert any("filename must be ASCII" in e for e in errors)


class TestLinks:
    def test_pdf_links_ok(self, tmp_path):
        notes_dir = make_vault(tmp_path, build_note())
        errors: list[str] = []
        validate_pdf_links(notes_dir, notes_dir / "sample-2026.md", build_note(), errors)
        assert errors == []

    def test_missing_source_pdf_frontmatter(self, tmp_path):
        notes_dir = make_vault(tmp_path, build_note())
        errors: list[str] = []
        text = build_note().replace('source_pdf: "raw/sample/source.pdf"\n', "")
        validate_pdf_links(notes_dir, notes_dir / "sample-2026.md", text, errors)
        assert any("missing source_pdf" in e for e in errors)

    def test_missing_pdf_file(self, tmp_path):
        notes_dir = make_vault(tmp_path, build_note())
        (notes_dir / "raw" / "sample" / "source.pdf").unlink()
        errors: list[str] = []
        validate_pdf_links(notes_dir, notes_dir / "sample-2026.md", build_note(), errors)
        assert any("source_pdf does not exist" in e for e in errors)

    def test_broken_wiki_link(self, tmp_path):
        text = build_note() + "\nSee [[no-such-note]].\n"
        notes_dir = make_vault(tmp_path, text)
        notes = [notes_dir / "sample-2026.md"]
        errors: list[str] = []
        validate_wiki_links(notes, {notes[0]: text}, errors)
        assert any("broken note link" in e for e in errors)

    def test_wiki_link_to_existing_note(self, tmp_path):
        text = build_note() + "\nSee [[other-note|the other one]].\n"
        notes_dir = make_vault(tmp_path, text)
        (notes_dir / "other-note.md").write_text(build_note(), encoding="utf-8")
        notes = [notes_dir / "sample-2026.md", notes_dir / "other-note.md"]
        errors: list[str] = []
        validate_wiki_links(notes, {notes[0]: text}, errors)
        assert errors == []


class TestFigures:
    def write_manifest(self, tmp_path: Path, items: list[dict]) -> Path:
        evidence_dir = tmp_path / "raw"
        figures = evidence_dir / "sample" / "figures"
        figures.mkdir(parents=True)
        (figures / "manifest.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        return evidence_dir

    def figure_line(self, n: int) -> str:
        return "\n".join(
            f"![[raw/sample/figures/files/{i:03d}-figure-{i}.png]]" for i in range(1, n + 1)
        )

    def test_counts_match(self, tmp_path):
        evidence_dir = self.write_manifest(
            tmp_path, [{"id": 1, "selected": True}, {"id": 2, "selected": True}]
        )
        text = build_note(self.figure_line(2))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("sample-2026.md"): text}, errors)
        assert errors == []

    def test_count_mismatch(self, tmp_path):
        evidence_dir = self.write_manifest(
            tmp_path, [{"id": 1, "selected": True}, {"id": 2, "selected": True}]
        )
        text = build_note(self.figure_line(1))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("sample-2026.md"): text}, errors)
        assert any("manifest=2" in e for e in errors)

    def test_skip_escape_hatch(self, tmp_path):
        evidence_dir = self.write_manifest(
            tmp_path, [{"id": 1, "selected": True}, {"id": 2, "selected": True, "skip": True}]
        )
        text = build_note(self.figure_line(1))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("sample-2026.md"): text}, errors)
        assert errors == []

    def test_out_of_scope_paper_is_skipped(self, tmp_path):
        """A raw folder no note claims yet is an unfinished run, not an error."""
        evidence_dir = self.write_manifest(
            tmp_path, [{"id": 1, "selected": True}, {"id": 2, "selected": True}]
        )
        other = evidence_dir / "unrelated-2025" / "figures"
        other.mkdir(parents=True)
        (other / "manifest.json").write_text(
            json.dumps({"items": [{"selected": True}] * 5}), encoding="utf-8"
        )
        text = build_note(self.figure_line(2))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("sample-2026.md"): text}, errors)
        assert errors == []

    def test_owner_note_is_matched_by_source_pdf_not_filename(self, tmp_path):
        """The raw folder name is the contract, not the note filename."""
        evidence_dir = self.write_manifest(tmp_path, [{"id": 1, "selected": True}])
        text = build_note(self.figure_line(1))
        errors: list[str] = []
        validate_figures(evidence_dir, {Path("totally-different-name.md"): text}, errors)
        assert errors == []

    def test_manifest_expected_items_shapes(self):
        assert manifest_expected_items({"items": [{"selected": True}, {"selected": True, "skip": True}]}) == 1
        assert manifest_expected_items("garbage") == 0
        assert manifest_expected_items({"items": [{"selected": True}, {"selected": False}]}) == 1


def test_frontmatter_value_quoted_and_bare():
    text = 'title: "A Paper"\nstatus: read\n'
    assert frontmatter_value(text, "title") == "A Paper"
    assert frontmatter_value(text, "status") == "read"
    assert frontmatter_value(text, "missing") == ""
