from pathlib import Path

from paper_notes.appendix import (
    AppendixDetection,
    apply_appendix_policy,
    detect_appendix,
)


def page(*lines: str) -> str:
    return "\n".join(lines)


def test_explicit_appendix_heading_is_high_confidence():
    text = "\f".join(
        [
            page("1 Introduction", "body"),
            page("2 Method", "body"),
            page("Appendix", "extra tables"),
        ]
    )
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page == 3
    assert detection.confidence == "high"
    assert detection.total_pages == 3


def test_lettered_appendix_after_references():
    text = "\f".join(
        [
            page("Body text", "more body"),
            page("References", "Smith 2020"),
            page("A. Additional Experiments", "tables"),
        ]
    )
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page == 3
    assert detection.confidence == "high"


def test_all_caps_lettered_appendix_after_references():
    text = "\f".join(
        [
            page("Body text", "more body"),
            page("References", "Smith 2020"),
            page("B ABLATION DETAILS", "tables"),
        ]
    )
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page == 3
    assert detection.confidence == "high"


def test_title_case_lettered_heading_is_deliberately_not_detected():
    """Conservative by design: 'A Additional Notes' is indistinguishable from a
    sentence starting with a single letter, so the detector refuses to guess."""
    text = "\f".join(
        [
            page("Body text", "more body"),
            page("References", "Smith 2020"),
            page("A Additional Experiments", "tables"),
        ]
    )
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page is None
    assert detection.confidence == "none"



def test_lettered_heading_before_references_is_ignored():
    text = "\f".join(
        [
            page("Body text", "more body"),
            page("Ablation Study Results", "our numbers"),
            page("References", "Smith 2020"),
        ]
    )
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page is None
    assert detection.confidence == "none"


def test_no_appendix_detected():
    text = "\f".join([page("Intro"), page("Method"), page("Results")])
    detection = detect_appendix(Path("dummy.pdf"), text=text)
    assert detection.start_page is None
    assert detection.total_pages == 3
    assert detection.reason == "no appendix heading detected"


def test_page_range_is_zero_based_and_exclusive_of_appendix():
    assert AppendixDetection(total_pages=20, start_page=18).page_range == "0-16"
    assert AppendixDetection(total_pages=20).page_range is None
    assert AppendixDetection(total_pages=20, start_page=1).page_range is None


def test_policy_full_disables_cutoff():
    detection = AppendixDetection(total_pages=20, start_page=18, confidence="high")
    applied = apply_appendix_policy(detection, "full")
    assert applied.start_page is None
    assert applied.confidence == "disabled"


def test_policy_override_is_honoured():
    detection = AppendixDetection(total_pages=20)
    applied = apply_appendix_policy(detection, "auto", override_start_page=15)
    assert applied.start_page == 15
    assert applied.confidence == "override"


def test_policy_rejects_out_of_range_override_and_bad_policy():
    detection = AppendixDetection(total_pages=20)
    for bad in (1, 21, 999):
        try:
            apply_appendix_policy(detection, "auto", override_start_page=bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for start page {bad}")
    try:
        apply_appendix_policy(detection, "sometimes")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown policy")


def body(n: int) -> list[str]:
    return [page(f"{i} Section", "body text") for i in range(1, n + 1)]


def test_appendix_heading_mid_page_is_found():
    """Two-column papers put the heading mid-page in reading-order text."""
    pages = body(9) + [page("6. Conclusions", "we conclude", "Appendix", "A. Formal Definitions")] + body(2) \
        + [page("References", "[1] Smith")]
    detection = detect_appendix(Path("dummy.pdf"), text="\f".join(pages))
    assert detection.start_page == 10


def test_appendix_before_references_and_sentences_rejected():
    pages = body(6) + [page("see the", "Appendix D for the full results.", "Appendix, we also show")] + body(3) \
        + [page("A. Datasets", "x", "B. Training Details")] + [page("References", "[1] a")]
    detection = detect_appendix(Path("dummy.pdf"), text="\f".join(pages))
    assert detection.start_page == 11 and "lettered" in detection.reason


def test_small_caps_appendix():
    pages = body(8) + [page("R EFERENCES", "[1] a")] + body(1) + [page("A PPENDIX", "A PPENDIX C ONTENTS")]
    assert detect_appendix(Path("dummy.pdf"), text="\f".join(pages)).start_page == 11


def test_table_of_contents_entry_does_not_cut_the_body():
    pages = [page("Contents", "Appendix")] + body(14) + [page("References", "[1] a")]
    detection = detect_appendix(Path("dummy.pdf"), text="\f".join(pages))
    assert detection.start_page is None


def test_lone_letter_headings_after_references():
    pages = body(9) + [page("References", "[1] a")] + body(1) + [page("A", "Hyperparameters", "text")] \
        + [page("B", "Ablations", "text")]
    assert detect_appendix(Path("dummy.pdf"), text="\f".join(pages)).start_page == 12


def test_lone_letter_panel_labels_in_body_are_ignored():
    pages = body(6) + [page("A", "Panel title", "B", "Other panel")] + body(5) + [page("References", "[1] a")]
    assert detect_appendix(Path("dummy.pdf"), text="\f".join(pages)).start_page is None
