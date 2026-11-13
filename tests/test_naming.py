import hashlib
import json
from pathlib import Path

from paper_notes.naming import ascii_slug, disambiguate_paper_id, paper_id, paper_id_from_pdf


class TestAsciiSlug:
    def test_plain_title(self):
        assert ascii_slug("Attention Is All You Need") == "attention-is-all-you-need"

    def test_punctuation_and_repeated_separators_collapse(self):
        assert ascii_slug("VGGT: Visual Geometry -- Grounded Transformer!") == (
            "vggt-visual-geometry-grounded-transformer"
        )

    def test_diacritics_are_folded(self):
        assert ascii_slug("Café Rêverie") == "cafe-reverie"

    def test_cjk_only_falls_back(self):
        assert ascii_slug("世界模型综述") == "paper"
        assert ascii_slug("世界模型综述", fallback="untitled") == "untitled"

    def test_leading_trailing_separators_stripped(self):
        assert ascii_slug("  ...DreamerV3...  ") == "dreamerv3"


class TestPaperId:
    def test_short_name_plus_year(self):
        assert paper_id(short_name="vggt", year=2025) == "vggt-2025"

    def test_title_used_without_short_name(self):
        assert paper_id(title="Attention Is All You Need", year=2017) == "attention-is-all-you-need-2017"

    def test_source_name_fallback(self):
        assert paper_id(source_name="DreamerV3.pdf", year=2023) == "dreamerv3-2023"

    def test_missing_year_does_not_add_trailing_dash(self):
        assert paper_id(short_name="vggt") == "vggt"
        assert paper_id(short_name="vggt", year="") == "vggt"
        assert paper_id(short_name="vggt", year="   ") == "vggt"

    def test_no_input_falls_back_to_paper(self):
        assert paper_id(year=2026) == "paper-2026"

    def test_paper_id_from_pdf_uses_descriptive_name(self):
        assert paper_id_from_pdf(Path("2501.12345v2.pdf")) == "2501-12345v2"


class TestDisambiguate:
    def test_unused_candidate_is_returned_unchanged(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        assert disambiguate_paper_id("vggt-2025", pdf, tmp_path / "raw") == "vggt-2025"

    def test_same_pdf_content_reuses_the_folder(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-2025").mkdir(parents=True)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        (raw / "vggt-2025" / "metadata.json").write_text(
            json.dumps({"sha256": digest}), encoding="utf-8"
        )
        assert disambiguate_paper_id("vggt-2025", pdf, raw) == "vggt-2025"

    def test_different_pdf_content_gets_short_suffix(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-2025").mkdir(parents=True)
        (raw / "vggt-2025" / "metadata.json").write_text(
            json.dumps({"sha256": "0" * 64}), encoding="utf-8"
        )
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:8]
        assert disambiguate_paper_id("vggt-2025", pdf, raw) == f"vggt-2025-{digest}"

    def test_missing_metadata_still_disambiguates(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-2025").mkdir(parents=True)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:8]
        assert disambiguate_paper_id("vggt-2025", pdf, raw) == f"vggt-2025-{digest}"
