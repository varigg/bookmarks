"""Smoke tests for the MCP search tool: validation and pass-through."""

import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from bookmarks.mcp_server import build_server
from tests.factories import summarised_item


@pytest.fixture
def server(open_service):
    return build_server(open_service)


def _call(server, **arguments) -> dict:
    content = asyncio.run(server.call_tool("search", arguments))
    return json.loads(content[0].text)


def test_search_passes_through_to_the_core(server, service):
    item = summarised_item(
        service,
        url="https://example.com/vanguard",
        title="Budgeting basics",
        summary="How to set a budget.",
        entities=["Vanguard"],
        note="from a friend",
    )
    service.embed()

    body = _call(server, query="Vanguard", types=["article"])

    assert body["legs"] == ["fts", "vector"]
    result = body["results"][0]
    assert result["id"] == item.id
    assert result["summary"] == "How to set a budget."
    assert result["entities"] == ["Vanguard"]
    assert result["note"] == "from a friend"
    assert result["score"] > 0
    assert result["ranks"]["fts"] == 1


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"query": ""},
        {"query": "x", "limit": 0},
        {"query": "x", "limit": "many"},
        {"query": "x", "status": ["archived"]},
    ],
)
def test_search_rejects_invalid_input(server, arguments):
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("search", arguments))


def test_limit_above_50_is_capped(server, service):
    for n in range(52):
        summarised_item(
            service,
            url=f"https://example.com/{n}",
            title=f"Gardening {n}",
            summary="About gardening.",
        )

    assert len(_call(server, query="gardening", limit=80)["results"]) == 50
