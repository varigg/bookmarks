"""The CLI composition root wires Settings into the production adapters."""

from bookmarks.cli import _service_opener
from bookmarks.settings import Settings


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
