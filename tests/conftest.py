import pytest

from bookmarks import create_app, datafile
from bookmarks.datafile import write_data
from bookmarks.model import init_bookmarks


@pytest.fixture
def app():
    app = create_app({"TESTING": True})
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
    """
    Fixture that creates a temporary bookmarks file and patches get_data_source.
    """
    # Create a temporary file
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test_bookmarks.js"
    p.write_text("var bookmarks = [];")

    # Patch get_data_source to return the temporary file path
    monkeypatch.setattr(datafile, "get_data_source", lambda: str(p))

    yield str(p)

    # Cleanup is handled by pytest's tmp_path fixture


@pytest.fixture(autouse=True)
def setup_data(bookmarks_file, sample_bookmark):
    """
    Fixture to set up test data before each test.
    """
    # Write sample data
    bookmarks = {"0": sample_bookmark}
    write_data(bookmarks.values())

    # Initialize model with the new file
    init_bookmarks()

    yield
