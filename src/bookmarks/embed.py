"""The embed step: which items need vectors, and storing them."""

import sqlite3
from dataclasses import dataclass
from typing import Protocol

import sqlite_vec

from bookmarks.db import transaction


class EmbedError(Exception):
    pass


class Embedder(Protocol):
    model: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def document_text(title: str | None, summary: str | None, note: str | None) -> str:
    """One vector per item from title + summary + note; entities stay out."""
    return "\n\n".join(part for part in (title, summary, note) if part)


def serialize(vector: list[float]) -> bytes:
    return sqlite_vec.serialize_float32(vector)


# An item lacking a vector for the model bound to the `?`.
_UNEMBEDDED = (
    "NOT EXISTS (SELECT 1 FROM embedding e WHERE e.item_id = item.id AND e.model = ?)"
)


def unembedded_count(conn: sqlite3.Connection, model: str) -> int:
    return conn.execute(
        f"SELECT COUNT(*) FROM item WHERE {_UNEMBEDDED}", (model,)
    ).fetchone()[0]


@dataclass
class EmbedReport:
    embedded: int = 0
    error: str | None = None


def run_embed(
    conn: sqlite3.Connection, embedder: Embedder, *, batch_size: int = 32
) -> EmbedReport:
    """Embed every item lacking a vector for the current model.

    Vectors of any other model are dropped, so changing the configured model
    re-embeds everything.
    """
    conn.execute("DELETE FROM embedding WHERE model != ?", (embedder.model,))
    report = EmbedReport()
    while True:
        rows = conn.execute(
            f"SELECT id, title, summary, note FROM item WHERE {_UNEMBEDDED} "
            "ORDER BY id LIMIT ?",
            (embedder.model, batch_size),
        ).fetchall()
        if not rows:
            return report
        texts = [document_text(r["title"], r["summary"], r["note"]) for r in rows]
        try:
            vectors = embedder.embed_documents(texts)
        except EmbedError as exc:
            report.error = str(exc)
            return report
        with transaction(conn):
            conn.executemany(
                "INSERT OR REPLACE INTO embedding (item_id, model, dims, vector) "
                "VALUES (?, ?, ?, ?)",
                [
                    (row["id"], embedder.model, len(vector), serialize(vector))
                    for row, vector in zip(rows, vectors, strict=True)
                ],
            )
        report.embedded += len(rows)
