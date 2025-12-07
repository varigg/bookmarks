import os

from bookmarks.datafile import write_data
from bookmarks.model import get_bookmarks, init_bookmarks

TEST_BOOKMARKS_FILE = os.path.join(os.getcwd(), "test_bookmarks.js")


def test_index_route(client):
    """
    Test the index route redirects to /bookmarks.
    """
    response = client.get("/")
    assert response.status_code == 302
    assert b"/bookmarks" in response.data


def test_bookmarks_route(client, sample_bookmark):
    """
    Test the bookmarks route returns a 200 status code and contains the sample bookmark.
    """
    response = client.get("/bookmarks")
    assert response.status_code == 200
    assert sample_bookmark["title"].encode() in response.data


def test_bookmark_detail_route(client, sample_bookmark):
    """
    Test the bookmark detail route returns the correct bookmark.
    """
    response = client.get("/bookmarks/0")
    assert response.status_code == 200
    assert sample_bookmark["title"].encode() in response.data
    assert sample_bookmark["description"].encode() in response.data


def test_bookmark_not_found(client):
    """
    Test accessing a non-existent bookmark returns 404.
    """
    response = client.get("/bookmarks/999")
    assert response.status_code == 404
    assert b"Bookmark not found" in response.data


def test_update_bookmark(client):
    """
    Test updating an existing bookmark.
    """
    new_data = {
        "title": "Updated Title",
        "description": "Updated Description",
        "tags": "updated, new",
    }
    response = client.post("/bookmarks/0/update", data=new_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Title" in response.data
    assert b"Updated Description" in response.data


def test_update_nonexistent_bookmark(client):
    """
    Test updating a non-existent bookmark returns 404.
    """
    new_data = {
        "title": "Updated Title",
        "description": "Updated Description",
        "tags": "updated, new",
    }
    response = client.post("/bookmarks/999/update", data=new_data)
    assert response.status_code == 404
    assert b"Bookmark not found" in response.data


def test_delete_bookmark(client, sample_bookmark):
    """
    Test deleting a bookmark.
    """
    # Add a second bookmark (will become ID "1" after init)
    bookmark = {
        "title": "Test Bookmark to Delete",
        "url": "http://test.com",
        "description": "To be deleted",
        "tags": ["delete"],
        "dateAdded": "2025-01-01T00:00:00+00:00",
    }
    bookmarks = get_bookmarks()
    # Add the new bookmark - it will be reassigned ID "1" after init
    bookmarks["temp"] = bookmark
    write_data(bookmarks.values())
    init_bookmarks()

    # Verify we have 2 bookmarks
    response = client.get("/bookmarks")
    assert b"Test Bookmark to Delete" in response.data
    assert sample_bookmark["title"].encode() in response.data

    # Delete the second bookmark (ID "1")
    response = client.post("/bookmarks/delete/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Bookmark deleted successfully" in response.data

    # Ensure the bookmark is deleted but the original remains
    response = client.get("/bookmarks")
    assert b"Test Bookmark to Delete" not in response.data
    assert sample_bookmark["title"].encode() in response.data


def test_description_filter(client):
    """
    Test filtering by description.
    """
    # Add a bookmark with specific description
    bookmark = {
        "title": "Unreachable Site",
        "url": "http://broken.com",
        "description": "URL not reachable",
        "tags": ["error"],
        "dateAdded": "2025-01-01T00:00:00+00:00",
    }
    bookmarks = get_bookmarks()
    bookmarks["888"] = bookmark
    write_data(bookmarks.values())
    init_bookmarks()

    # Test filter
    response = client.get("/bookmarks?description=URL%20not%20reachable")
    assert response.status_code == 200
    assert b"Unreachable Site" in response.data

    # Test filter mismatch
    response = client.get("/bookmarks?description=SomethingElse")
    assert response.status_code == 200
    assert b"Unreachable Site" not in response.data


def test_gemini_tag_filter(client):
    """
    Test filtering by 'Summarized by Gemini' tag.
    """
    # Add a bookmark with specific tag
    bookmark = {
        "title": "Gemini Summary",
        "url": "http://gemini.com",
        "description": "A summary.",
        "tags": ["Summarized by Gemini"],
        "dateAdded": "2025-01-01T00:00:00+00:00",
    }
    bookmarks = get_bookmarks()
    bookmarks["777"] = bookmark
    write_data(bookmarks.values())
    init_bookmarks()

    # Test filter
    response = client.get("/bookmarks?tag=Summarized%20by%20Gemini")
    assert response.status_code == 200
    assert b"Gemini Summary" in response.data
