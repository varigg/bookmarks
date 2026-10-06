"""Scripted fakes for the core's external edges."""

import hashlib
import json
import math
import re

from bookmarks.embed import EmbedError
from bookmarks.ingest.fetch import FetchError, HttpResponse
from bookmarks.ingest.llm.provider import LLMRequest, LLMResult


class FakeFetcher:
    """Responses scripted per URL; an unscripted URL cannot be reached."""

    def __init__(self) -> None:
        self.routes: dict[str, list] = {}
        self.requests: list[tuple[str, dict]] = []

    def script(self, url: str, *responses) -> None:
        """Each fetch of `url` takes the next response; the last one repeats."""
        self.routes[url] = list(responses)

    def page(self, url: str, html: str, status: int = 200) -> None:
        self.script(url, HttpResponse(status=status, text=html))

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        self.requests.append((url, headers or {}))
        responses = self.routes.get(url)
        if not responses:
            raise FetchError(f"unscripted URL {url}")
        response = responses.pop(0) if len(responses) > 1 else responses[0]
        if isinstance(response, Exception):
            raise response
        return response


def summary_json(
    title: str = "A Title",
    type: str = "article",
    summary: str = "A lede that stands alone. More detail follows here.",
    entities: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "title": title,
            "type": type,
            "summary": summary,
            "entities": entities if entities is not None else ["CRDT"],
        }
    )


class FakeSummariser:
    """Replies scripted in order; the last one repeats. Records every request."""

    name = "claude-cli"

    def __init__(self, model: str = "claude-sonnet-5-5") -> None:
        self.model = model
        self.replies: list = [summary_json()]
        self.requests: list[LLMRequest] = []

    def script(self, *replies) -> None:
        self.replies = list(replies)

    def submit(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(text=reply, model=self.model)


# Words that share a meaning share a dimension, so a paraphrase lands near the
# text it paraphrases; every other word gets a weak hashed dimension.
_CONCEPTS = [
    {"collaborative", "collaboration", "collaborate", "collaborators", "merge",
     "merged", "merging", "concurrent", "concurrently", "sync", "syncing",
     "together", "multiplayer", "replicated", "editing", "edits"},
    {"offline", "local", "device", "devices", "laptop", "phone", "own",
     "ownership", "cloud", "server", "servers"},
    {"recipe", "bread", "sourdough", "bake", "baking", "flour", "oven", "loaf"},
    {"tax", "taxes", "budget", "money", "invest", "investing", "savings"},
]  # fmt: skip
_DIMS = 64
_WORD = re.compile(r"[a-z]+")


class FakeEmbedder:
    """Deterministic vectors from a tiny concept table. Refuses prefixed text,
    because callers must never add the embedder's prefixes."""

    def __init__(self, model: str = "fake-embed") -> None:
        self.model = model
        self.documents: list[str] = []
        self.queries: list[str] = []
        self.failure: Exception | None = None

    def _vector(self, text: str) -> list[float]:
        assert not text.startswith("search_"), "caller added an embedding prefix"
        vector = [0.0] * _DIMS
        for word in _WORD.findall(text.lower()):
            for index, concept in enumerate(_CONCEPTS):
                if word in concept:
                    vector[index] += 1.0
                    break
            else:
                bucket = int(hashlib.md5(word.encode()).hexdigest(), 16)
                vector[len(_CONCEPTS) + bucket % (_DIMS - len(_CONCEPTS))] += 0.2
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.failure:
            raise self.failure
        self.documents += texts
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.failure:
            raise self.failure
        self.queries.append(text)
        return self._vector(text)

    def fail(self, message: str = "ollama unreachable") -> None:
        self.failure = EmbedError(message)
