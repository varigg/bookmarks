"""Merging and renaming types; a merged-away name never comes back."""

import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from bookmarks.mcp_server import build_server
from tests.factories import item_at, summarised_item


@pytest.fixture
def server(open_service):
    return build_server(open_service)


def _merge(server, **arguments) -> dict:
    content = asyncio.run(server.call_tool("merge_types", arguments))
    return json.loads(content[0].text)


def _item(service, url, type):
    return summarised_item(service, url=url, title="T", summary="S.", type=type)


def test_merge_moves_items_and_list_types_reflects_it(server, service):
    _item(service, "https://example.com/a", "paper")
    _item(service, "https://example.com/b", "paper")
    _item(service, "https://example.com/c", "article")

    assert _merge(server, source="paper", into="Article") == {"moved": 2}

    types = service.list_types()
    assert "paper" not in types
    assert types["article"] == 3
    assert item_at(service, "https://example.com/a").type == "article"


def test_merge_into_a_new_name_renames(service):
    _item(service, "https://example.com/a", "paper")

    service.merge_types("paper", "research")

    assert service.list_types()["research"] == 1
    assert "paper" not in service.list_types()


def test_a_later_summary_naming_the_alias_is_stored_under_the_target(
    service, summariser
):
    _item(service, "https://example.com/a", "paper")
    service.merge_types("paper", "research")

    item = _item(service, "https://example.com/b", "Paper")

    assert item.type == "research"
    assert "paper" not in service.list_types()


def test_the_alias_is_never_offered_to_the_summariser(service, summariser):
    _item(service, "https://example.com/a", "paper")
    service.merge_types("paper", "research")
    service.merge_types("research", "article")

    item = _item(service, "https://example.com/b", "paper")

    prompt = summariser.requests[-1].user_prompt
    offered = next(line for line in prompt.splitlines() if "Types in use" in line)
    assert offered == "Types in use: article, discussion, docs, media, product, repo"
    assert item.type == "article"


@pytest.mark.parametrize(
    "arguments",
    [
        {"source": "nonesuch", "into": "article"},
        {"source": "article", "into": " ARTICLE "},
        {"source": "repo", "into": "paper"},
        {"source": "article", "into": ""},
    ],
)
def test_merge_refuses_bad_requests(server, service, arguments):
    _item(service, "https://example.com/a", "paper")
    service.merge_types("paper", "docs")

    with pytest.raises(ToolError):
        _merge(server, **arguments)
