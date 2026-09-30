"""SQLite connection and schema.

`connect` and `_load_sqlite_vec` are copied and adapted from adventure-library
`src/adventure_library/db.py` at commit b264b17.
"""

import sqlite3
from pathlib import Path

# Each entry moves the schema up one `PRAGMA user_version`; never edit a
# shipped entry, append a new one.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE item (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL UNIQUE,
        domain TEXT NOT NULL,
        title TEXT,
        type TEXT,
        summary TEXT,
        entities TEXT NOT NULL DEFAULT '[]',
        note TEXT,
        saved_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'summarised', 'failed')),
        failure_reason TEXT,
        prov_cli TEXT,
        prov_model TEXT,
        prov_prompt_hash TEXT,
        prov_at TEXT,
        prov_truncated INTEGER
    );
    CREATE INDEX idx_item_saved_at ON item (saved_at);
    CREATE INDEX idx_item_status ON item (status);

    -- Work waiting for the drain. The row exists only while there is work;
    -- the client html lives here and goes with the row.
    CREATE TABLE queue (
        item_id INTEGER PRIMARY KEY REFERENCES item (id) ON DELETE CASCADE,
        html TEXT,
        capture_title TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        claimed_at TEXT,
        enqueued_at TEXT NOT NULL
    );
    """,
    """
    -- The open type list: base types plus any the summariser adopts.
    CREATE TABLE type (
        name TEXT PRIMARY KEY,
        base INTEGER NOT NULL DEFAULT 0
    );
    INSERT INTO type (name, base) VALUES
        ('article', 1), ('repo', 1), ('docs', 1),
        ('product', 1), ('discussion', 1), ('media', 1);
    """,
]


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
        try:
            conn.enable_load_extension(False)
        except sqlite3.Error:
            pass


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        # executescript commits any open transaction first, so each script
        # carries its own BEGIN/COMMIT around the version bump.
        conn.executescript(f"BEGIN; {script}; PRAGMA user_version = {number}; COMMIT;")


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
        migrate(conn)
    except Exception:
        conn.close()
        raise
    return conn
