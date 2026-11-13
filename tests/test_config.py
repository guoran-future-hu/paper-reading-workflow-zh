import json

from paper_notes.config import PaperNotesConfig


def test_defaults_are_local(monkeypatch, tmp_path):
    for name in (
        "PAPER_NOTES_PDF_INBOX",
        "PAPER_NOTES_READING_INBOX",
        "PAPER_NOTES_ARCHIVE_ROOT",
        "MINERU_LOCAL_URL",
        "PAPER_NOTES_EXTRACTION_BACKEND",
        "DATALAB_API_KEY",
        "PAPER_NOTES_APPENDIX_POLICY",
        "PAPER_NOTES_APPENDIX_START_PAGE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    config = PaperNotesConfig.defaults()
    assert config.pdf_inbox == tmp_path / "inbox" / "pdfs"
    assert config.reading_inbox == tmp_path / "vault" / "reading"
    assert config.archive_root == tmp_path / "vault" / "notes"
    assert config.mineru_url == "http://127.0.0.1:8010"
    assert config.extraction_backend == "datalab"
    assert config.datalab_api_key == ""
    assert config.appendix_policy == "auto"
    assert config.appendix_start_page is None


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("PAPER_NOTES_PDF_INBOX", str(tmp_path / "papers"))
    monkeypatch.setenv("MINERU_LOCAL_URL", "http://127.0.0.1:9999/")
    monkeypatch.setenv("PAPER_NOTES_EXTRACTION_BACKEND", "mineru")
    monkeypatch.setenv("PAPER_NOTES_APPENDIX_START_PAGE", "18")
    config = PaperNotesConfig.defaults()
    assert config.pdf_inbox == tmp_path / "papers"
    assert config.mineru_url == "http://127.0.0.1:9999"
    assert config.extraction_backend == "mineru"
    assert config.appendix_start_page == 18


def test_from_file_overrides_and_derived_paths(monkeypatch, tmp_path):
    monkeypatch.delenv("MINERU_LOCAL_URL", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "pdf_inbox": str(tmp_path / "inbox"),
                "reading_inbox": str(tmp_path / "vault"),
                "mineru_url": "http://127.0.0.1:8010/",
                "datalab_api_key": "test-key",
                "appendix_policy": "full",
            }
        ),
        encoding="utf-8",
    )
    config = PaperNotesConfig.from_file(config_path)
    assert config.pdf_inbox == tmp_path / "inbox"
    assert config.mineru_url == "http://127.0.0.1:8010"
    assert config.datalab_api_key == "test-key"
    assert config.appendix_policy == "full"
    assert config.inbox_evidence_root == tmp_path / "vault" / "raw"
    assert config.reading_index == tmp_path / "vault" / "reading-index.md"


def test_public_dict_never_leaks_the_api_key(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"reading_inbox": str(tmp_path / "vault"), "datalab_api_key": "secret-value"}),
        encoding="utf-8",
    )
    public = PaperNotesConfig.from_file(config_path).to_public_dict()
    assert "datalab_api_key" not in public
    assert "secret-value" not in json.dumps(public)


def test_from_file_rejects_non_object(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("[]", encoding="utf-8")
    try:
        PaperNotesConfig.from_file(config_path)
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-object config")
