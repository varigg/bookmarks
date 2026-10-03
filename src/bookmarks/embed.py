"""Embedding edge and the embed step.

The Ollama adapter is adapted from adventure-library
`src/adventure_library/embeddings.py` (OllamaProvider) at commit b264b17.
"""

import sqlite3
from dataclasses import dataclass
from typing import Protocol

import httpx
import sqlite_vec

from bookmarks.db import transaction

# nomic-embed-text is trained with task prefixes; they are applied here and
# nowhere else.
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class EmbedError(Exception):
    pass


class Embedder(Protocol):
    model: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    def __init__(
        self,
        model: str,
        url: str,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.url = url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed([DOCUMENT_PREFIX + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self.client.post(
                f"{self.url}/api/embed", json={"model": self.model, "input": texts}
            )
            response.raise_for_status()
            vectors = response.json()["embeddings"]
        except httpx.HTTPError as exc:
            raise EmbedError(f"ollama unreachable at {self.url}: {exc}") from None
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbedError(f"ollama returned invalid embeddings: {exc}") from None
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbedError("ollama returned the wrong number of embeddings")
        try:
            vectors = [[float(v) for v in vector] for vector in vectors]
        except (TypeError, ValueError) as exc:
            raise EmbedError(f"ollama returned invalid embeddings: {exc}") from None
        if not vectors[0] or any(len(v) != len(vectors[0]) for v in vectors):
            raise EmbedError("ollama returned embeddings of inconsistent size")
        return vectors


def document_text(title: str | None, summary: str | None, note: str | None) -> str:
    """One vector per item from title + summary + note; entities stay out."""
    return "\n\n".join(part for part in (title, summary, note) if part)


def serialize(vector: list[float]) -> bytes:
    return sqlite_vec.serialize_float32(vector)


@dataclass
class EmbedReport:
    embedded: int = 0
    error: str | None = None


def run_embed(
    conn: sqlite3.Connection, embedder: Embedder, *, batch_size: int = 32
) -> EmbedReport:
    """Embed every summarised item lacking a vector for the current model.

    Vectors of any other model are dropped, so changing the configured model
    re-embeds everything.
    """
    conn.execute("DELETE FROM embedding WHERE model != ?", (embedder.model,))
    report = EmbedReport()
    while True:
        rows = conn.execute(
            "SELECT id, title, summary, note FROM item "
            "WHERE status = 'summarised' AND NOT EXISTS ("
            "  SELECT 1 FROM embedding e WHERE e.item_id = item.id AND e.model = ?"
            ") ORDER BY id LIMIT ?",
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
