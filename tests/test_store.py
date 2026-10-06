"""The store's insert: complete items only, one per URL."""

import pytest

from bookmarks import store

PROVENANCE = store.Provenance(
    cli="claude-cli",
    model="m",
    prompt_hash="abc",
    at="2026-09-30T12:00:00Z",
    truncated=False,
)


def _insert(conn, url="https://example.com/a", type="article"):
    return store.insert_item(
        conn,
        url=url,
        title="A",
        type=type,
        summary="An article.",
        entities=["CRDT"],
        note=None,
        saved_at="2026-09-01T00:00:00Z",
        provenance=PROVENANCE,
    )


def test_insert_stores_a_complete_item(conn):
    item = store.get_by_id(conn, _insert(conn))

    assert item.domain == "example.com"
    assert item.entities == ["CRDT"]
    assert item.saved_at == "2026-09-01T00:00:00Z"
    assert item.provenance == PROVENANCE


def test_insert_refuses_a_url_that_already_has_an_item(conn):
    _insert(conn)

    with pytest.raises(store.ItemExists):
        _insert(conn, type="paper")

    assert "paper" not in store.types_in_use(conn)


def test_insert_adopts_an_unseen_type(conn):
    _insert(conn, type="paper")

    assert "paper" in store.types_in_use(conn)
