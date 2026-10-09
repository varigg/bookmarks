"""Backup: a consistent copy of the store on the separate media disk."""

import sqlite3
from datetime import datetime
from pathlib import Path

from bookmarks.alert import Alerter

PREFIX = "bookmarks-"
SUFFIX = ".db"


def run_backup(
    conn: sqlite3.Connection,
    *,
    target: Path,
    alerter: Alerter,
    now: datetime,
    keep: int = 14,
) -> Path | None:
    """Copy the store into `target`, keep the newest `keep` copies.

    `target` must already exist: the operator chose it, and a missing one (say,
    its disk is not mounted) must not be silently recreated on the wrong disk.
    That emails the operator and returns None.
    """
    if not target.is_dir():
        alerter.send(
            "bookmarks backup skipped",
            f"{target} does not exist; no backup was written.",
        )
        return None
    final = target / f"{PREFIX}{now:%Y%m%dT%H%M%SZ}{SUFFIX}"
    partial = final.with_suffix(".part")
    # sqlite3's online backup API copies a consistent snapshot while writers run.
    copy = sqlite3.connect(partial)
    try:
        conn.backup(copy)
    finally:
        copy.close()
    partial.replace(final)
    for old in sorted(target.glob(f"{PREFIX}*{SUFFIX}"))[:-keep]:
        old.unlink()
    return final
