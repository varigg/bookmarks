"""Backup copies the store consistently, prunes, and refuses a missing target."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from bookmarks import db
from bookmarks.alert import AlertError, MsmtpAlerter
from bookmarks.backup import run_backup

START = datetime(2026, 10, 9, 2, 0, tzinfo=UTC)


class RecordingAlerter:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, subject: str, body: str) -> None:
        self.sent.append((subject, body))


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "live.db")
    yield connection
    connection.close()


def backup(conn, tmp_path, alerter, day=0, keep=14, make_dir=True):
    target = tmp_path / "backups"
    if make_dir:
        target.mkdir(exist_ok=True)
    return run_backup(
        conn,
        target=target,
        alerter=alerter,
        now=START + timedelta(days=day),
        keep=keep,
    )


def test_a_backup_is_a_consistent_copy_of_the_store(conn, tmp_path):
    made = backup(conn, tmp_path, RecordingAlerter())

    copy = sqlite3.connect(made)
    names = "SELECT name FROM type ORDER BY name"
    live = [tuple(r) for r in conn.execute(names)]
    assert copy.execute(names).fetchall() == live != []
    assert copy.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    copy.close()


def test_only_the_newest_copies_are_kept(conn, tmp_path):
    for day in range(5):
        backup(conn, tmp_path, RecordingAlerter(), day=day, keep=3)

    kept = sorted(p.name for p in (tmp_path / "backups").iterdir())
    assert kept == [
        "bookmarks-20261011T020000Z.db",
        "bookmarks-20261012T020000Z.db",
        "bookmarks-20261013T020000Z.db",
    ]


def test_a_missing_target_writes_nothing_and_sends_an_email(conn, tmp_path):
    alerter = RecordingAlerter()

    assert backup(conn, tmp_path, alerter, make_dir=False) is None

    assert not (tmp_path / "backups").exists()
    assert len(alerter.sent) == 1
    assert "does not exist" in alerter.sent[0][1]


def test_msmtp_failure_is_reported(tmp_path):
    script = tmp_path / "fake-msmtp"
    script.write_text("#!/bin/sh\ncat >/dev/null\necho relay down >&2\nexit 7\n")
    script.chmod(0o755)

    with pytest.raises(AlertError, match="relay down"):
        MsmtpAlerter("me@example.com", executable=str(script)).send("s", "b")
