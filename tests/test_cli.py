"""The CLI composition root wires Settings into the production adapters."""

import pytest

from bookmarks import cli
from bookmarks.cli import _service_opener
from bookmarks.settings import Settings
from tests.factories import fixture_text


def test_service_opener_configures_the_summariser_from_settings(tmp_path):
    settings = Settings(
        db_path=tmp_path / "bookmarks.db",
        claude_executable="/opt/claude",
        summariser_model="claude-haiku-4-5",
        summariser_timeout=42,
    )

    with _service_opener(settings)() as svc:
        summariser = svc.summariser

    assert summariser.executable == "/opt/claude"
    assert summariser.model == "claude-haiku-4-5"
    assert summariser.timeout == 42


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
