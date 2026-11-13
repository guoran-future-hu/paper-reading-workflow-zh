import hashlib
import json

from paper_notes.naming import ascii_slug, disambiguate_paper_id


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



class TestDisambiguate:
    def test_unused_candidate_is_returned_unchanged(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        assert disambiguate_paper_id("vggt-visual-geometry-grounded-transformer", pdf, tmp_path / "raw") == "vggt-visual-geometry-grounded-transformer"

    def test_same_pdf_content_reuses_the_folder(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-visual-geometry-grounded-transformer").mkdir(parents=True)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        (raw / "vggt-visual-geometry-grounded-transformer" / "metadata.json").write_text(
            json.dumps({"sha256": digest}), encoding="utf-8"
        )
        assert disambiguate_paper_id("vggt-visual-geometry-grounded-transformer", pdf, raw) == "vggt-visual-geometry-grounded-transformer"

    def test_different_pdf_content_gets_short_suffix(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-visual-geometry-grounded-transformer").mkdir(parents=True)
        (raw / "vggt-visual-geometry-grounded-transformer" / "metadata.json").write_text(
            json.dumps({"sha256": "0" * 64}), encoding="utf-8"
        )
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:8]
        assert disambiguate_paper_id("vggt-visual-geometry-grounded-transformer", pdf, raw) == f"vggt-visual-geometry-grounded-transformer-{digest}"

    def test_missing_metadata_still_disambiguates(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 a")
        raw = tmp_path / "raw"
        (raw / "vggt-visual-geometry-grounded-transformer").mkdir(parents=True)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:8]
        assert disambiguate_paper_id("vggt-visual-geometry-grounded-transformer", pdf, raw) == f"vggt-visual-geometry-grounded-transformer-{digest}"
