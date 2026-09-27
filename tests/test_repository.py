from bookmarks.data.datafile import get_data, write_data
from bookmarks.data.repository import BookmarkRepository


def _bm(title):
    return {"url": f"https://{title}.example", "title": title, "description": "", "tags": []}


def test_legacy_file_gets_positional_ids():
    write_data([_bm("a"), _bm("b"), _bm("c")])

    repo = BookmarkRepository()

    assert {k: v["title"] for k, v in repo.get_all().items()} == {"0": "a", "1": "b", "2": "c"}


def test_ids_stable_after_delete_and_reload():
    write_data([_bm("a"), _bm("b"), _bm("c")])
    repo = BookmarkRepository()

    repo.delete("0")
    reloaded = BookmarkRepository()

    assert reloaded.get_by_id("0") is None
    assert reloaded.get_by_id("1")["title"] == "b"
    assert reloaded.get_by_id("2")["title"] == "c"


def test_ids_are_persisted_in_data_file():
    write_data([_bm("a"), _bm("b")])
    repo = BookmarkRepository()

    repo.delete("0")

    assert [bm["id"] for bm in get_data()] == ["1"]


def test_new_id_after_reload_does_not_collide():
    write_data([_bm("a"), _bm("b"), _bm("c")])
    repo = BookmarkRepository()
    repo.delete("1")

    reloaded = BookmarkRepository()
    new_id = reloaded.generate_new_id()

    assert new_id == "3"


def test_entries_missing_id_are_numbered_after_existing_ids():
    write_data([{**_bm("a"), "id": "7"}, _bm("b")])

    repo = BookmarkRepository()

    assert repo.get_by_id("7")["title"] == "a"
    assert repo.get_by_id("8")["title"] == "b"
