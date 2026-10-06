"""Item records and the SQL that reads and writes them."""

import json
import sqlite3
from dataclasses import dataclass

from bookmarks.urls import InvalidUrl as InvalidUrl
from bookmarks.urls import domain_of, normalise_url


@dataclass(frozen=True)
class Provenance:
    cli: str
    model: str
    prompt_hash: str
    at: str
    truncated: bool


@dataclass(frozen=True)
class Item:
    id: int
    url: str
    domain: str
    title: str
    type: str
    summary: str
    entities: list[str]
    note: str | None
    saved_at: str
    provenance: Provenance


def identity(url: str) -> str:
    """An item's identity is its normalised URL. Raises `InvalidUrl`."""
    return normalise_url(url)


class ItemExists(Exception):
    """The URL already has an item; the producer decides what that means."""


def item_from_row(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"],
        url=row["url"],
        domain=row["domain"],
        title=row["title"],
        type=row["type"],
        summary=row["summary"],
        entities=json.loads(row["entities"]),
        note=row["note"],
        saved_at=row["saved_at"],
        provenance=Provenance(
            cli=row["prov_cli"],
            model=row["prov_model"],
            prompt_hash=row["prov_prompt_hash"],
            at=row["prov_at"],
            truncated=bool(row["prov_truncated"]),
        ),
    )


def get_by_id(conn: sqlite3.Connection, item_id: int) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
    return item_from_row(row) if row is not None else None


def get_by_url(conn: sqlite3.Connection, url: str) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE url = ?", (identity(url),)).fetchone()
    return item_from_row(row) if row is not None else None


def insert_item(
    conn: sqlite3.Connection,
    *,
    url: str,
    title: str,
    type: str,
    summary: str,
    entities: list[str],
    note: str | None,
    saved_at: str,
    provenance: Provenance,
) -> int:
    """Add a complete item and adopt its Type if unseen. Raises `ItemExists`.

    Runs inside the caller's transaction, if any."""
    url = identity(url)
    try:
        item_id = conn.execute(
            "INSERT INTO item (url, domain, title, type, summary, entities, note, "
            "saved_at, prov_cli, prov_model, prov_prompt_hash, prov_at, "
            "prov_truncated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "RETURNING id",
            (
                url,
                domain_of(url),
                title,
                type,
                summary,
                json.dumps(entities),
                note,
                saved_at,
                provenance.cli,
                provenance.model,
                provenance.prompt_hash,
                provenance.at,
                int(provenance.truncated),
            ),
        ).fetchone()[0]
    except sqlite3.IntegrityError as exc:
        if get_by_url(conn, url) is None:
            raise
        raise ItemExists(url) from exc
    conn.execute("INSERT OR IGNORE INTO type (name) VALUES (?)", (type,))
    return item_id


def types_in_use(conn: sqlite3.Connection) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM type ORDER BY name")]
