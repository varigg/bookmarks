from unittest.mock import MagicMock, patch

import pytest

from bookmarks.core.exceptions import BookmarkNotFoundError
from bookmarks.services.bookmark_service import BookmarkService


@pytest.fixture
def service():
    return BookmarkService()


def test_get_all_tags_sorting(service):
    # Mock repository
    service.repository = MagicMock()
    service.repository.get_all.return_value = {
        "1": {"tags": ["python", "coding"]},
        "2": {"tags": ["python", "ai"]},
        "3": {"tags": ["coding", "testing"]},
        "4": {"tags": ["python"]},
    }

    tags = service.get_all_tags()

    # python: 3, coding: 2, ai: 1, testing: 1
    # Sorting: count DESC, then name ASC
    expected_order = ["python", "coding", "ai", "testing"]
    assert list(tags.keys()) == expected_order
    assert tags["python"] == 3
    assert tags["coding"] == 2


def test_toggle_favorite_not_found(service):
    service.repository = MagicMock()
    service.repository.get_by_id.return_value = None

    with pytest.raises(BookmarkNotFoundError):
        service.toggle_favorite("999")


def test_toggle_favorite_success(service):
    service.repository = MagicMock()
    service.repository.get_by_id.return_value = {"favorite": False, "title": "Test"}

    result = service.toggle_favorite("1")
    assert result["favorite"] is True
    service.repository.save.assert_called_once()


def test_update_bookmark_not_found(service):
    service.repository = MagicMock()
    service.repository.get_by_id.return_value = None

    with pytest.raises(BookmarkNotFoundError):
        service.update_bookmark("999", title="New Title")


def test_create_bookmark_with_llm_success(service):
    # Mock generate_metadata
    with patch.object(service, "generate_metadata") as mock_gen:
        mock_gen.return_value = {"title": "LLM Title", "description": "LLM Desc"}

        # Mock create_bookmark
        with patch.object(service, "create_bookmark") as mock_create:
            mock_create.return_value = ("new_id", {"title": "LLM Title"})

            id, data = service.create_bookmark_with_llm("https://example.com")

            assert id == "new_id"
            mock_gen.assert_called_once_with("https://example.com")
            mock_create.assert_called_once()
