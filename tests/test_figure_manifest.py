from pathlib import Path

from paper_notes.figure_manifest import (
    clean_caption,
    has_visual_evidence,
    label_kind,
    safe_name,
)
from paper_notes.naming import paper_id_from_pdf


class TestVisualEvidence:
    def test_image_with_caption_and_bbox(self):
        item = {
            "type": "image",
            "bbox": [10, 10, 500, 300],
            "page_idx": 0,
            "image_caption": ["Figure 1: The Transformer - model architecture."],
        }
        assert has_visual_evidence(item)

    def test_text_block_rejected(self):
        assert not has_visual_evidence({"type": "text", "bbox": [0, 0, 1, 1], "page_idx": 0})

    def test_missing_bbox_rejected(self):
        assert not has_visual_evidence({"type": "image", "page_idx": 0, "image_caption": ["A long enough caption"]})

    def test_short_caption_without_table_body_rejected(self):
        assert not has_visual_evidence(
            {"type": "image", "bbox": [0, 0, 1, 1], "page_idx": 0, "image_caption": ["tiny"]}
        )


class TestLabels:
    def test_figure_number_extracted(self):
        assert label_kind("Figure 2: Attention weights", "image", 7) == "figure-2"

    def test_table_number_extracted(self):
        assert label_kind("Table 3: BLEU scores", "table", 7) == "table-3"

    def test_fallback_by_type(self):
        assert label_kind("no numbering here", "table", 4) == "table-004"
        assert label_kind("no numbering here", "chart", 4) == "chart-004"
        assert label_kind("no numbering here", "image", 4) == "figure-004"

    def test_safe_name(self):
        assert safe_name("Figure 1: 模型结构!") == "figure-1"
        assert safe_name("") == "visual"


def test_clean_caption_prefers_caption_over_body():
    item = {"image_caption": ["Figure 1:  spaced   caption"], "text": "body"}
    assert clean_caption(item) == "Figure 1: spaced caption"


def test_clean_caption_strips_html_from_table_body():
    item = {"table_body": "<table><tr><td>cell</td></tr></table>"}
    assert clean_caption(item) == "cell"


def test_paper_id_from_pdf_name():
    assert paper_id_from_pdf(Path("Attention Is All You Need.pdf")) == "attention-is-all-you-need"
    assert paper_id_from_pdf(Path("你好.pdf")) == "paper"
