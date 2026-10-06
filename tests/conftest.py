from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from bookmarks import db
from bookmarks.service import Bookmarks
from bookmarks.settings import Settings
from tests.fakes import FakeEmbedder, FakeFetcher, FakeSummariser


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(db_path=tmp_path / "bookmarks.db")


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


@pytest.fixture
def summariser() -> FakeSummariser:
    return FakeSummariser()


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def conn(settings):
    connection = db.connect(settings.db_path)
    yield connection
    connection.close()


@pytest.fixture
def make_service(conn, settings, fetcher, summariser, embedder):
    """Build the core over the real temp-dir SQLite; override any collaborator."""

    def build(**overrides) -> Bookmarks:
        collaborators = {
            "settings": settings,
            "fetcher": fetcher,
            "summariser": summariser,
            "embedder": embedder,
        }
        collaborators.update(overrides)
        return Bookmarks(conn, **collaborators)

    return build


@pytest.fixture
def service(make_service) -> Bookmarks:
    return make_service()


@pytest.fixture
def open_service(service):
    @contextmanager
    def opener() -> Iterator[Bookmarks]:
        yield service

    return opener
