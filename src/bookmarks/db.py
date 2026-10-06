"""SQLite connection and schema.

`connect` and `_load_sqlite_vec` are copied and adapted from adventure-library
`src/adventure_library/db.py` at commit b264b17.
"""

import contextlib
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

# Stored timestamp form: UTC, second precision, trailing Z.
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def now_iso() -> str:
    """Now in stored timestamp form."""
    return datetime.now(UTC).strftime(TIMESTAMP_FORMAT)


SCHEMA = """
    -- An item exists only once it is summarised (ADR 0002).
    CREATE TABLE item (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL UNIQUE,
        domain TEXT NOT NULL,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        summary TEXT NOT NULL,
        entities TEXT NOT NULL DEFAULT '[]',
        note TEXT,
        saved_at TEXT NOT NULL,
        prov_cli TEXT NOT NULL,
        prov_model TEXT NOT NULL,
        prov_prompt_hash TEXT NOT NULL,
        prov_at TEXT NOT NULL,
        prov_truncated INTEGER NOT NULL
    );
    CREATE INDEX idx_item_saved_at ON item (saved_at);

    -- A URL waiting to become an item; the row goes once the item exists.
    -- The capture surface's html lives here until retrieving replaces it
    -- with the source text, which stays until summarising finishes.
    CREATE TABLE submission (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL UNIQUE,
        note TEXT,
        saved_at TEXT NOT NULL,
        html TEXT,
        capture_title TEXT,
        source_text TEXT,
        source_title TEXT,
        source_description TEXT,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'failed')),
        failure_reason TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        claimed_at TEXT,
        enqueued_at TEXT NOT NULL
    );
    -- The open type list: base types plus any the summariser adopts.
    CREATE TABLE type (
        name TEXT PRIMARY KEY,
        base INTEGER NOT NULL DEFAULT 0
    );
    INSERT INTO type (name, base) VALUES
        ('article', 1), ('repo', 1), ('docs', 1),
        ('product', 1), ('discussion', 1), ('media', 1);
    -- One vector per item per embedding model (title + summary + note).
    CREATE TABLE embedding (
        item_id INTEGER NOT NULL REFERENCES item (id) ON DELETE CASCADE,
        model TEXT NOT NULL,
        dims INTEGER NOT NULL,
        vector BLOB NOT NULL,
        PRIMARY KEY (item_id, model)
    );
    -- A vector is stale once the text it was made from changes.
    CREATE TRIGGER item_embedding_stale
    AFTER UPDATE OF title, summary, note ON item
    BEGIN
        DELETE FROM embedding WHERE item_id = old.id;
    END;

    -- External-content FTS5 over the item, kept in sync by triggers.
    -- Column order matters: bm25() weights are positional.
    CREATE VIRTUAL TABLE item_fts USING fts5 (
        title, summary, note, entities,
        content = 'item', content_rowid = 'id'
    );
    CREATE TRIGGER item_fts_ai AFTER INSERT ON item BEGIN
        INSERT INTO item_fts (rowid, title, summary, note, entities)
        VALUES (new.id, new.title, new.summary, new.note, new.entities);
    END;
    CREATE TRIGGER item_fts_ad AFTER DELETE ON item BEGIN
        INSERT INTO item_fts (item_fts, rowid, title, summary, note, entities)
        VALUES ('delete', old.id, old.title, old.summary, old.note, old.entities);
    END;
    CREATE TRIGGER item_fts_au
    AFTER UPDATE OF title, summary, note, entities ON item BEGIN
        INSERT INTO item_fts (item_fts, rowid, title, summary, note, entities)
        VALUES ('delete', old.id, old.title, old.summary, old.note, old.entities);
        INSERT INTO item_fts (rowid, title, summary, note, entities)
        VALUES (new.id, new.title, new.summary, new.note, new.entities);
    END;
"""


def _load_sqlite_vec(conn: sqlite3.Connection) -> None:
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception as exc:
        raise RuntimeError(
            "sqlite-vec could not be loaded; install the sqlite-vec dependency "
            "and use a Python SQLite build that supports extension loading"
        ) from exc
    finally:
        with contextlib.suppress(sqlite3.Error):
            conn.enable_load_extension(False)


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """BEGIN IMMEDIATE ... COMMIT, rolled back on any exception."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        _load_sqlite_vec(conn)
        if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
            conn.executescript(f"BEGIN; {SCHEMA}; PRAGMA user_version = 1; COMMIT;")
    except Exception:
        conn.close()
        raise
    return conn
