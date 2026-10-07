"""Pipeline status: the core, and the MCP tool and console panel over it."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from bookmarks.mcp_server import build_server
from bookmarks.web.app import create_app
from tests.factories import is_recent, summarised_item

OLD = "2026-01-01T00:00:00Z"


@pytest.fixture
def busy(service, fetcher):
    """1 failed, 3 items (1 unembedded), 2 pending: the oldest saved at OLD."""
    fetcher.page("https://example.com/gone", "gone", status=404)
    service.save("https://example.com/gone")
    service.drain()
    for n in range(2):
        summarised_item(service, url=f"https://example.com/{n}", title="t", summary="s")
    service.embed()
    summarised_item(service, url="https://example.com/late", title="t", summary="s")
    service.save("https://example.com/old", saved_at=OLD)
    service.save("https://example.com/new")
    return service


def test_status_of_an_empty_store(service):
    status = service.status()

    assert status.last_successful_drain is None
    assert status.oldest_pending_since is None
    assert status.oldest_pending_hours is None
    assert (status.pending, status.failed, status.items, status.unembedded) == (
        0,
        0,
        0,
        0,
    )


def test_status_counts_ages_and_last_drain(busy):
    status = busy.status()

    assert (status.pending, status.failed, status.items, status.unembedded) == (
        2,
        1,
        3,
        1,
    )
    assert status.oldest_pending_since == OLD
    assert status.oldest_pending_hours > 24 * 200
    assert is_recent(status.last_successful_drain)


def test_mcp_status_tool(busy, open_service):
    content = asyncio.run(build_server(open_service).call_tool("status", {}))

    status = json.loads(content[0].text)
    assert status["pending"] == 2
    assert status["oldest_pending_since"] == OLD
    assert status["unembedded"] == 1


def test_console_shows_the_status_panel(busy, open_service):
    page = TestClient(create_app(open_service)).get("/").text

    for text in ("2 pending", "1 failed", "3 items", "1 unembedded", OLD):
        assert text in page
