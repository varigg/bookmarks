"""The legacy importer: old URLs become pending submissions at their dates."""

from bookmarks import cli
from bookmarks.ingest import legacy
from tests.factories import FIXTURES, fixture_text, submission_at

LEGACY = fixture_text("legacy_bookmarks.js")


def test_parse_reads_the_array_despite_the_js_around_it():
    assert legacy.parse(LEGACY) == [
        legacy.LegacyBookmark(
            "https://example.com/gaza?utm_source=facebook&id=7#comments",
            "2024-07-28T07:15:02Z",
        ),
        legacy.LegacyBookmark("https://example.org/post", "2026-10-02T20:11:33Z"),
    ]


def test_import_saves_pending_submissions_at_the_original_dates(service):
    outcomes = legacy.import_legacy(service, legacy.parse(LEGACY))

    assert outcomes == {"saved": 2}
    sub = submission_at(service, "https://example.com/gaza?id=7")
    assert sub.status == "pending"
    assert sub.saved_at == "2024-07-28T07:15:02Z"
    assert sub.note is None
    row = service.conn.execute(
        "SELECT capture_title, html FROM submission WHERE url = ?", (sub.url,)
    ).fetchone()
    assert tuple(row) == (None, None)


def test_importing_twice_creates_no_duplicates(service):
    legacy.import_legacy(service, legacy.parse(LEGACY))

    outcomes = legacy.import_legacy(service, legacy.parse(LEGACY))

    assert outcomes == {"already_saved": 2}
    assert service.conn.execute("SELECT COUNT(*) FROM submission").fetchone()[0] == 2


def test_cli_import_reports_the_counts(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "b.db"))
    monkeypatch.setenv("BOOKMARKS_OLLAMA_URL", "http://ollama.test:11434")

    cli.main(["import-legacy", str(FIXTURES / "legacy_bookmarks.js")])

    assert capsys.readouterr().out.strip() == (
        "import: 2 read, 2 saved, 0 already saved, 0 re-queued"
    )
