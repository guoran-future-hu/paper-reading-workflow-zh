import json
import subprocess
import sys

import pytest

from paper_notes.html_extract import collect_figures, figure_filename, fill_references
from paper_notes.init_paper import init_paper
from paper_notes.reading_index import upsert_row
from paper_notes.scaffold_note import render_note, summarizer_sections
from paper_notes.select_figures import apply_selection
from paper_notes.split_text import assemble, is_empty

PDF = b"%PDF-1.4\n%fake\n"


class TestInit:
    def test_id_is_title_slug_and_rerun_is_stable(self, tmp_path):
        pdf = tmp_path / "2503.11651.pdf"
        pdf.write_bytes(PDF)
        root = tmp_path / "raw"
        pid, paper_dir = init_paper(pdf, "VGGT: Visual Geometry Grounded Transformer", root)
        assert pid == "vggt-visual-geometry-grounded-transformer"
        assert (paper_dir / "source.pdf").read_bytes() == PDF
        assert (paper_dir / "text").is_dir() and (paper_dir / "figures" / "files").is_dir()
        meta = json.loads((paper_dir / "metadata.json").read_text())
        assert meta["title"].startswith("VGGT") and meta["source_pdf"] == f"raw/{pid}/source.pdf"
        assert init_paper(pdf, "VGGT: Visual Geometry Grounded Transformer", root)[0] == pid

    def test_same_title_different_pdf_gets_suffix(self, tmp_path):
        root = tmp_path / "raw"
        a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
        a.write_bytes(PDF)
        b.write_bytes(PDF + b"other")
        first, _ = init_paper(a, "Same Title", root)
        second, _ = init_paper(b, "Same Title", root)
        assert first == "same-title" and second.startswith("same-title-") and second != first

    def test_rejects_non_pdf(self, tmp_path):
        bad = tmp_path / "x.pdf"
        bad.write_text("<html>")
        with pytest.raises(SystemExit):
            init_paper(bad, "T", tmp_path / "raw")


class TestHtmlFigures:
    MD = "\n".join([
        "## 1 Intro",
        "![Refer to caption](arch.png)",
        "Figure 1: The architecture.",
        "## References",
        "## Appendix A Extra",
        "![](extra.png)",
    ])

    def test_captions_and_appendix_flag(self):
        figures = collect_figures(self.MD)
        assert [f["src"] for f in figures] == ["arch.png", "extra.png"]
        assert figures[0]["caption"] == "Figure 1: The architecture." and not figures[0]["appendix"]
        assert figures[1]["appendix"]

    def test_filename_uses_paper_figure_number(self):
        assert figure_filename(1, "Figure 3: x", "https://a/b/anatomy.png") == "001-figure-3-anatomy.png"

    def test_fill_only_empty_references(self):
        md = "## References\n\n## Appendix\ntext\n"
        filled = fill_references(md, ["[1] A. Paper."])
        assert "- [1] A. Paper." in filled and filled.endswith("## Appendix\ntext\n")
        kept = "## References\n[1] already there\n"
        assert fill_references(kept, ["[1] other"]) == kept


class TestSplit:
    def test_partition_check_and_local_fallback(self, tmp_path):
        (tmp_path / "appendix-local.md").write_text("Appendix A from pdftotext " * 5)
        source = "# Body\ntext\n## References\n[1] x\n"
        outputs, origin = assemble(source, "# Body\ntext\n", "## References\n[1] x\n",
                                   "<!-- No appendix -->\n", tmp_path)
        assert origin == {"references": "split", "appendix": "appendix-local.md"}
        assert outputs["appendix.md"].startswith("Appendix A")

    def test_lossy_split_is_rejected(self, tmp_path):
        with pytest.raises(SystemExit):
            assemble("abc", "a", "<!-- No -->", "<!-- No -->", tmp_path)

    def test_heading_only_section_counts_as_empty(self):
        assert is_empty("## References\n\n") and not is_empty("## References\n" + "[1] a real entry. " * 5)

    def test_real_prune_script_partitions(self, tmp_path):
        from paper_notes.split_text import SPLIT_SCRIPT, run_split

        if not SPLIT_SCRIPT.is_file():
            pytest.skip("prune-paper skill not installed on this machine")
        src = tmp_path / "full_text.md"
        src.write_text("# T\nbody\n## References\n[1] r\n## Appendix A\napp\n")
        pruned, refs, appendix = run_split(src)
        assert pruned + refs + appendix == src.read_text()


class TestSelectScaffoldIndex:
    MANIFEST = {"items": [
        {"id": 1, "path": "raw/p/figures/files/001.png", "caption": "Figure 1", "selected": False},
        {"id": 2, "path": "raw/p/figures/files/002.png", "caption": "Figure 2", "selected": False},
    ]}

    def test_selection_replaces_and_skip(self):
        manifest = apply_selection(json.loads(json.dumps(self.MANIFEST)), [1, 2], [2], [])
        assert [i["selected"] for i in manifest["items"]] == [True, True]
        assert manifest["items"][1]["skip"] is True
        with pytest.raises(SystemExit):
            apply_selection(manifest, [9], [], [])

    def test_scaffold_takes_sections_from_summarizer_skill(self):
        manifest = apply_selection(json.loads(json.dumps(self.MANIFEST)), [2], [], [])
        skill = "# S\n\n## Output\n\n```md\n# <Paper Title>\n\n- Authors\n\n## 1. Abstract\nShorter abstract.\n\n" \
                "## 2. How It Works\nThe machine.\n```\n\n## Fidelity\n- x\n"
        note = render_note({"paper_id": "p", "title": "P"}, manifest, skill, "A", "2025", ["x"], "2026-01-01")
        assert "## 1. Abstract\n\n<!-- TODO Shorter abstract. -->" in note
        assert "## 2. How It Works" in note and "## Fidelity" not in note and "<Paper Title>" not in note
        assert note.count("raw/p/figures/files/") == 1 and "![[raw/p/source.pdf]]" in note
        assert "## Key Figures" not in note and "![[raw/p/figures/files/002.png]]  Fig. 2" in note
        assert "<!-- TODO Place each figure" in note
        assert "<!-- TODO - Authors -->" in note

    def test_scaffold_rejects_skill_without_output_block(self):
        with pytest.raises(SystemExit):
            summarizer_sections("# S\n\n## Writing\n- x\n")

    def test_real_summarizer_skill_parses(self):
        from paper_notes.scaffold_note import SUMMARIZER_SKILL

        if not SUMMARIZER_SKILL.is_file():
            pytest.skip("paper-summarizer skill not installed on this machine")
        _, sections = summarizer_sections(SUMMARIZER_SKILL.read_text(encoding="utf-8"))
        assert len(sections) >= 3

    def test_index_upsert_dedupes_and_keeps_topic(self):
        text = "# Reading Index\n\n| Paper | Year | Status | Topic |\n| --- | ---: | --- | --- |\n" \
               "| [[a]] | 2020 | read | old topic |\n\n| [[b]] | 2021 | read | t |\n"
        out = upsert_row(text, "a", "2020", "read", "")
        assert out.count("[[a]]") == 1 and "old topic" in out and "|\n\n| [[" not in out
        assert upsert_row(out, "c", "2024", "read", "new").strip().endswith("| [[c]] | 2024 | read | new |")


def test_datalab_cli_refuses_bare_run():
    proc = subprocess.run([sys.executable, "-m", "paper_notes.datalab_extract"], capture_output=True, text=True)
    assert proc.returncode != 0 and "never batch-extracted implicitly" in proc.stderr


def test_paper_caption_skips_extractor_description():
    from paper_notes.figure_manifest import paper_caption

    desc = "Figure 2: Architecture Overview. The diagram illustrates the camera head producing depth maps."
    md = f"text\n![{desc}](abc_img.jpg)\n\n{desc}\n\nFigure 2. **Architecture Overview.** Our model patchifies.\n"
    assert paper_caption(md, "abc_img.jpg", desc) == "Figure 2. Architecture Overview. Our model patchifies."
    assert paper_caption(md, "missing.jpg", desc) == ""


def test_appendix_before_references_moves_out_of_pruned(tmp_path):
    source = "# T\nbody\n## Appendix\n### A. Defs\nx\n## References\n[1] r\n"
    outputs, origin = assemble(source, "# T\nbody\n## Appendix\n### A. Defs\nx\n", "## References\n[1] r\n",
                               "<!-- No appendix (reference section runs to EOF) -->\n", tmp_path)
    assert outputs["pruned.md"] == "# T\nbody\n" and outputs["appendix.md"].startswith("## Appendix")
    assert origin["appendix"] == "moved from before References"
