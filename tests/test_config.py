import json

from paper_notes.config import PaperNotesConfig


def test_defaults_are_local(monkeypatch, tmp_path):
    for name in (
        "PAPER_NOTES_PDF_INBOX",
        "PAPER_NOTES_READING_INBOX",
        "PAPER_NOTES_ARCHIVE_ROOT",
        "PAPER_NOTES_STAGING_ROOT",
        "MINERU_LOCAL_URL",
        "EVIDENCE_DEEP_READ_VALIDATOR",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    config = PaperNotesConfig.defaults()
    assert config.pdf_inbox == tmp_path / "inbox" / "pdfs"
    assert config.mineru_url == "http://127.0.0.1:8010"
    assert config.evidence_deep_read_validator is None


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("PAPER_NOTES_PDF_INBOX", str(tmp_path / "papers"))
    monkeypatch.setenv("MINERU_LOCAL_URL", "http://127.0.0.1:9999/")
    config = PaperNotesConfig.defaults()
    assert config.pdf_inbox == tmp_path / "papers"
    assert config.mineru_url == "http://127.0.0.1:9999"


def test_from_file_overrides_and_derived_paths(monkeypatch, tmp_path):
    monkeypatch.delenv("MINERU_LOCAL_URL", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "pdf_inbox": str(tmp_path / "inbox"),
                "reading_inbox": str(tmp_path / "vault" / "论文阅读"),
                "mineru_url": "http://127.0.0.1:8010/",
            }
        ),
        encoding="utf-8",
    )
    config = PaperNotesConfig.from_file(config_path)
    assert config.pdf_inbox == tmp_path / "inbox"
    assert config.mineru_url == "http://127.0.0.1:8010"
    assert config.read_marker_dir == tmp_path / "inbox" / "已读标记"
    assert config.reading_index == tmp_path / "vault" / "论文阅读" / "论文阅读记录.md"


def test_from_file_rejects_non_object(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("[]", encoding="utf-8")
    try:
        PaperNotesConfig.from_file(config_path)
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-object config")
