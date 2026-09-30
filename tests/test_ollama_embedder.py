"""The Ollama adapter owns the nomic task prefixes and the response checks."""

import json

import httpx
import pytest

from bookmarks.embed import EmbedError, OllamaEmbedder


def _embedder(handler) -> OllamaEmbedder:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OllamaEmbedder("nomic-embed-text", "http://127.0.0.1:11434/", client=client)


def _echo(sent: list):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append((str(request.url), body))
        return httpx.Response(
            200, json={"embeddings": [[0.1, 0.2]] * len(body["input"])}
        )

    return handler


def test_documents_and_queries_get_their_prefixes():
    sent: list = []
    embedder = _embedder(_echo(sent))

    embedder.embed_documents(["title\n\nsummary"])
    embedder.embed_query("loose words")

    assert sent[0][0] == "http://127.0.0.1:11434/api/embed"
    assert sent[0][1] == {
        "model": "nomic-embed-text",
        "input": ["search_document: title\n\nsummary"],
    }
    assert sent[1][1]["input"] == ["search_query: loose words"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(200, json={"nope": []}),
        httpx.Response(200, json={"embeddings": []}),
        httpx.Response(200, json={"embeddings": [["x"]]}),
    ],
)
def test_bad_responses_raise_embed_error(response):
    embedder = _embedder(lambda request: response)
    with pytest.raises(EmbedError):
        embedder.embed_query("q")


def test_unreachable_ollama_raises_embed_error():
    def refuse(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(EmbedError, match="unreachable"):
        _embedder(refuse).embed_documents(["t"])
