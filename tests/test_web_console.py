"""Smoke tests for the web console: each page passes through to the core."""

import pytest
from fastapi.testclient import TestClient

from bookmarks.web.app import create_app
from tests.factories import item_at, summarised_item


@pytest.fixture
def client(open_service):
    return TestClient(create_app(open_service))


@pytest.fixture
def items(service):
    made = {
        "essay": summarised_item(
            service,
            url="https://inkandswitch.com/local-first",
            title="Local-first software",
            summary="Collaborative apps can merge edits offline. More follows.",
            entities=["Automerge"],
            note="read for the sync design",
            saved_at="2026-09-01T12:00:00Z",
        ),
        "repo": summarised_item(
            service,
            url="https://codeberg.org/automerge/automerge",
            title="automerge/automerge",
            summary="A library of data structures for collaborative apps.",
            type="repo",
            saved_at="2026-09-02T12:00:00Z",
        ),
        "bread": summarised_item(
            service,
            url="https://bakery.example.org/sourdough",
            title="A sourdough loaf",
            summary="A recipe for baking sourdough bread at home.",
            saved_at="2026-09-03T12:00:00Z",
        ),
    }
    service.embed()
    return made


def _titles_in_order(html: str, items: dict) -> list[str]:
    found = [(html.find(i.title), i.title) for i in items.values() if i.title in html]
    return [title for _, title in sorted(found)]


def test_list_shows_items_newest_first(client, items):
    response = client.get("/")

    assert response.status_code == 200
    assert _titles_in_order(response.text, items) == [
        "A sourdough loaf",
        "automerge/automerge",
        "Local-first software",
    ]


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"type": "repo"}, ["automerge/automerge"]),
        ({"domain": "example.org"}, ["A sourdough loaf"]),
        (
            {"type": "", "domain": ""},
            ["A sourdough loaf", "automerge/automerge", "Local-first software"],
        ),
    ],
)
def test_list_filters_by_type_and_domain(client, items, params, expected):
    response = client.get("/", params=params)

    assert _titles_in_order(response.text, items) == expected


def test_search_box_returns_hybrid_results(client, items):
    response = client.get("/", params={"q": "Automerge"})

    # No relevance cutoff: the bread still lists, but ranked below the matches.
    titles = _titles_in_order(response.text, items)
    assert set(titles[:2]) == {"Local-first software", "automerge/automerge"}


def test_detail_shows_the_full_record(client, items):
    item = items["essay"]

    response = client.get(f"/items/{item.id}")

    assert response.status_code == 200
    for text in (
        item.summary,
        "Automerge",
        "read for the sync design",
        item.provenance.model,
        item.provenance.prompt_hash,
        "https://web.archive.org/web/https://inkandswitch.com/local-first",
    ):
        assert text in response.text


def test_detail_of_a_missing_item_is_404(client):
    assert client.get("/items/999").status_code == 404


def test_delete_removes_the_item_and_returns_to_the_list(client, service, items):
    item = items["bread"]

    response = client.post(f"/items/{item.id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert item_at(service, item.url) is None


def test_delete_of_a_missing_item_is_404(client):
    assert client.post("/items/999/delete").status_code == 404
