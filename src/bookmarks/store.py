"""Item records and the SQL that reads them."""

import json
import sqlite3
from dataclasses import dataclass


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
    title: str | None
    type: str | None
    summary: str | None
    entities: list[str]
    note: str | None
    saved_at: str
    status: str
    failure_reason: str | None
    provenance: Provenance | None


def item_from_row(row: sqlite3.Row) -> Item:
    provenance = None
    if row["prov_cli"] is not None:
        provenance = Provenance(
            cli=row["prov_cli"],
            model=row["prov_model"],
            prompt_hash=row["prov_prompt_hash"],
            at=row["prov_at"],
            truncated=bool(row["prov_truncated"]),
        )
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
        status=row["status"],
        failure_reason=row["failure_reason"],
        provenance=provenance,
    )


def get_by_id(conn: sqlite3.Connection, item_id: int) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
    return item_from_row(row) if row is not None else None


def get_by_url(conn: sqlite3.Connection, url: str) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE url = ?", (url,)).fetchone()
    return item_from_row(row) if row is not None else None
