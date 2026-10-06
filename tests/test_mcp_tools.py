"""Smoke tests for the MCP read/write tools over the real core."""

import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from bookmarks import store
from bookmarks.mcp_server import build_server
from tests.factories import item_at, summarised_item


@pytest.fixture
def server(open_service):
    return build_server(open_service)


def _call(server, tool, **arguments) -> dict:
    content = asyncio.run(server.call_tool(tool, arguments))
    return json.loads(content[0].text)


def _item(service, url="https://example.com/a", **fields):
    defaults = {
        "title": "Budgeting basics",
        "summary": "How to set a budget. It covers envelopes.",
    }
    return summarised_item(service, url=url, **(defaults | fields))


def test_list_items_newest_first_with_lede(server, service):
    _item(service, url="https://example.com/old", saved_at="2026-01-01T00:00:00Z")
    _item(service, url="https://example.com/new", saved_at="2026-02-01T00:00:00Z")

    items = _call(server, "list_items")["items"]

    assert [i["url"] for i in items] == [
        "https://example.com/new",
        "https://example.com/old",
    ]
    assert items[0]["lede"] == "How to set a budget."


def test_get_item_by_id_and_by_unnormalised_url(server, service):
    item = _item(service)

    by_id = _call(server, "get_item", id=item.id)
    by_url = _call(server, "get_item", url="https://example.com/a?utm_source=x#top")

    assert by_id == by_url
    assert by_id["provenance"]["prompt_hash"] == service.prompt.hash
    assert by_id["archive_url"] == "https://web.archive.org/web/https://example.com/a"


@pytest.mark.parametrize(
    "arguments", [{}, {"id": 1, "url": "https://example.com/a"}, {"id": 999}]
)
def test_get_item_refuses_bad_or_unknown_lookups(server, arguments):
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("get_item", arguments))


def test_save_item_behaves_like_a_capture_save(server, service):
    url = "https://example.com/fails"
    service.fetcher.page(url, "", status=404)

    saved = _call(server, "save_item", url=url, note="my reason")
    again = _call(server, "save_item", url=url, note="other")
    pending = _call(server, "list_submissions", status="pending")["submissions"]
    service.drain()
    failed = _call(server, "list_submissions", status="failed")["submissions"]
    requeued = _call(server, "save_item", url=url)

    assert (saved["outcome"], saved["note_added"]) == ("saved", True)
    assert (again["outcome"], again["note_added"]) == ("already_saved", False)
    assert [s["url"] for s in pending] == [url]
    assert failed[0]["failure_reason"].startswith("retrieving: not found")
    assert requeued["outcome"] == "requeued"


def test_save_item_refuses_a_non_http_url(server):
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("save_item", {"url": "ftp://example.com"}))


def test_delete_item_removes_it_from_lists_and_search(server, service):
    item = _item(service, entities=["Vanguard"])
    service.embed()
    assert _call(server, "search", query="Vanguard budget")["results"]

    deleted = _call(server, "delete_item", url="https://example.com/a")

    assert deleted["deleted"]["id"] == item.id
    assert item_at(service, item.url) is None
    assert _call(server, "list_items")["items"] == []
    assert _call(server, "search", query="Vanguard budget")["results"] == []
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("delete_item", {"id": item.id}))


def test_list_types_counts_items_per_type(server, service):
    _item(service, url="https://example.com/a")
    _item(service, url="https://example.com/b")
    _item(service, url="https://example.com/p", type="paper")

    types = {t["name"]: t["count"] for t in _call(server, "list_types")["types"]}

    assert types["article"] == 2
    assert types["paper"] == 1
    assert types["repo"] == 0


def test_lede_is_the_first_sentence():
    assert store.lede("One thing. Two things!") == "One thing."
    assert store.lede("Just one") == "Just one"
