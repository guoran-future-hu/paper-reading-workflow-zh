from paper_notes.download import (
    arxiv_id_from_text,
    arxiv_pdf_from_id,
    pdf_url_from_url,
    sanitize_filename,
    select_arxiv_candidate,
    title_match_score,
)


class TestArxivIdFromText:
    def test_abs_url(self):
        assert arxiv_id_from_text("https://arxiv.org/abs/1706.03762v5") == "1706.03762"

    def test_pdf_url(self):
        assert arxiv_id_from_text("see arxiv.org/pdf/2401.12345 for details") == "2401.12345"

    def test_arxiv_prefix(self):
        assert arxiv_id_from_text("arXiv:2401.12345v2") == "2401.12345"

    def test_bare_id_full_query(self):
        assert arxiv_id_from_text("1706.03762") == "1706.03762"
        assert arxiv_id_from_text("  1706.03762v3  ") == "1706.03762"

    def test_id_shaped_number_inside_title_is_not_an_id(self):
        # A title containing an ID-shaped number must fall through to title search.
        assert arxiv_id_from_text("Benchmark 2024.12345 for Reasoning Models") is None

    def test_plain_title(self):
        assert arxiv_id_from_text("Attention Is All You Need") is None


class TestPdfUrlFromUrl:
    def test_abs_to_pdf(self):
        assert pdf_url_from_url("https://arxiv.org/abs/1706.03762") == "https://arxiv.org/pdf/1706.03762"

    def test_versioned_abs(self):
        assert pdf_url_from_url("https://arxiv.org/abs/1706.03762v5") == "https://arxiv.org/pdf/1706.03762"

    def test_direct_pdf_kept(self):
        assert pdf_url_from_url("https://example.com/paper.pdf") == "https://example.com/paper.pdf"

    def test_pdf_with_query_kept(self):
        assert pdf_url_from_url("https://example.com/paper.pdf?dl=1") == "https://example.com/paper.pdf?dl=1"

    def test_non_pdf_passthrough(self):
        assert pdf_url_from_url("https://openreview.net/forum?id=abc") == "https://openreview.net/forum?id=abc"


class TestTitleMatchScore:
    def test_exact(self):
        assert title_match_score("Attention Is All You Need", "attention is all you need") == 1.0

    def test_full_coverage_few_extras(self):
        assert title_match_score("Attention Is All You Need", "Attention Is All You Need (Extended)") == 0.94

    def test_partial_coverage_below_threshold(self):
        assert title_match_score("Attention Is All You Need", "Attention Mechanisms Survey") < 0.92

    def test_empty(self):
        assert title_match_score("", "anything") == 0.0


class TestSelectArxivCandidate:
    def test_rejects_low_confidence(self):
        rows = [{"title": "Something Entirely Different", "id": "1111.11111"}]
        candidate, scored = select_arxiv_candidate("Attention Is All You Need", rows)
        assert candidate is None
        assert scored

    def test_accepts_exact_and_enriches_pdf(self):
        rows = [{"title": "Attention Is All You Need", "id": "1706.03762"}]
        candidate, _ = select_arxiv_candidate("Attention Is All You Need", rows)
        assert candidate is not None
        assert candidate["pdf"] == "https://arxiv.org/pdf/1706.03762"


class TestFilenames:
    def test_sanitize_strips_bad_chars(self):
        assert sanitize_filename('A/B: C?"D"') == "A B C D"

    def test_sanitize_caps_length(self):
        assert len(sanitize_filename("x" * 500)) == 180

    def test_sanitize_empty_fallback(self):
        assert sanitize_filename("///") == "paper"

    def test_arxiv_pdf_strips_version(self):
        assert arxiv_pdf_from_id("1706.03762v5") == "https://arxiv.org/pdf/1706.03762"


def test_run_json_unwraps_opencli_v2_envelope(monkeypatch):
    import subprocess as sp

    from paper_notes import download

    def fake(stdout):
        return lambda *a, **k: sp.CompletedProcess(a, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(download.subprocess, "run", fake('{"ok":true,"data":[{"id":"1","title":"T"}]}'))
    assert download.run_json(["opencli"]) == [{"id": "1", "title": "T"}]
    monkeypatch.setattr(download.subprocess, "run", fake('{"ok":false,"error":{"code":"EMPTY","message":"none"}}'))
    try:
        download.run_json(["opencli"])
    except RuntimeError as exc:
        assert "EMPTY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
