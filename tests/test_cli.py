"""The CLI composition root wires Settings into the production adapters."""

import pytest

from bookmarks import cli
from bookmarks.cli import _service_opener
from bookmarks.settings import Settings
from tests.factories import fixture_text


def test_service_opener_configures_the_summariser_from_settings(tmp_path):
    settings = Settings(
        db_path=tmp_path / "bookmarks.db",
        ollama_url="http://ollama.test:11434",
        claude_executable="/opt/claude",
        summariser_model="claude-haiku-4-5",
        summariser_timeout=42,
    )

    with _service_opener(settings)() as svc:
        summariser = svc.summariser

    assert summariser.executable == "/opt/claude"
    assert summariser.model == "claude-haiku-4-5"
    assert summariser.timeout == 42


def test_service_opener_needs_an_ollama_url(tmp_path):
    with pytest.raises(SystemExit, match="BOOKMARKS_OLLAMA_URL"):
        _service_opener(Settings(db_path=tmp_path / "bookmarks.db"))


def test_retrieve_prints_the_source_text(monkeypatch, capsys, fetcher):
    fetcher.page("https://example.com/post", fixture_text("article.html"))
    monkeypatch.setattr(cli, "HttpxFetcher", lambda timeout: fetcher)

    cli.main(["retrieve", "https://example.com/post"])

    assert "Conflict-free Replicated Data Types" in capsys.readouterr().out


def test_retrieve_reports_a_failure_and_exits_nonzero(monkeypatch, capsys, fetcher):
    fetcher.page("https://example.com/gone", "gone", status=404)
    monkeypatch.setattr(cli, "HttpxFetcher", lambda timeout: fetcher)

    with pytest.raises(SystemExit) as exit_:
        cli.main(["retrieve", "https://example.com/gone"])

    assert exit_.value.code == 1
    assert capsys.readouterr().err.strip() == "not found (HTTP 404)"


def test_backup_needs_a_backup_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "b.db"))
    monkeypatch.delenv("BOOKMARKS_BACKUP_DIR", raising=False)

    with pytest.raises(SystemExit, match="BOOKMARKS_BACKUP_DIR"):
        cli.main(["backup"])


def test_backup_needs_an_alert_address(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "b.db"))
    monkeypatch.setenv("BOOKMARKS_BACKUP_DIR", str(tmp_path / "out"))
    monkeypatch.delenv("BOOKMARKS_ALERT_TO", raising=False)

    with pytest.raises(SystemExit, match="BOOKMARKS_ALERT_TO"):
        cli.main(["backup"])


def test_backup_to_a_missing_directory_alerts_and_exits_nonzero(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "b.db"))
    monkeypatch.setenv("BOOKMARKS_ALERT_TO", "me@example.com")
    monkeypatch.setenv("BOOKMARKS_BACKUP_DIR", str(tmp_path / "gone"))
    monkeypatch.setattr(
        cli,
        "MsmtpAlerter",
        lambda to: type("A", (), {"send": lambda s, *a: sent.append(a)})(),
    )

    with pytest.raises(SystemExit, match="does not exist"):
        cli.main(["backup"])

    assert len(sent) == 1
    assert not (tmp_path / "gone").exists()
