import pytest

from bookmarks import create_app, datafile
from bookmarks.data.datafile import write_data
from bookmarks.data.repository import BookmarkRepository


@pytest.fixture
def app(bookmarks_file):
    """Create app with patched data source bound to a per-test file."""
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for tests
            "CSRF_ENABLED": False,  # Alternative config key
        }
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_bookmark():
    return {
        "url": "https://example.com",
        "title": "Example Bookmark",
        "description": "A sample bookmark for testing.",
        "tags": ["test", "example"],
        "dateAdded": "2025-01-01T00:00:00+00:00",
    }


@pytest.fixture
def bookmarks_file(tmp_path, monkeypatch):
    """Per-test data file path patched into the datafile helper."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    data_path = data_dir / "test_bookmarks.js"
    data_path.write_text("var bookmarks = [];")

    # Patch get_data_source to use the per-test file
    monkeypatch.setattr(datafile, "get_data_source", lambda: str(data_path))

    yield str(data_path)

    # Cleanup handled by tmp_path


@pytest.fixture(autouse=True)
def isolate_bookmarks_storage(app, bookmarks_file):
    """Reset repository state and storage to an empty, per-test file."""
    with app.app_context():
        from bookmarks.web.routes import get_bookmark_service

        # Reset the in-memory repository to point at the patched data source
        get_bookmark_service().repository = BookmarkRepository()

        # Ensure the file starts empty for this test
        write_data([])

    yield


@pytest.fixture
def setup_data(bookmarks_file, sample_bookmark):
    """
    Fixture to set up test data before each test.
    """
    bookmarks = {"0": sample_bookmark}
    write_data(bookmarks.values())

    yield
