"""Ollama embedding edge. The core sees `Embedder` or `EmbedError`, never httpx.

Adapted from adventure-library `src/adventure_library/embeddings.py`
(OllamaProvider) at commit b264b17.
"""

import httpx

from bookmarks.embed import EmbedError

# nomic-embed-text is trained with task prefixes; they are applied here and
# nowhere else.
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


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
