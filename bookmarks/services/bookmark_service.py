"""Service layer for bookmark business logic."""

import logging
from datetime import UTC, datetime

from bookmarks import config
from bookmarks.core.exceptions import BookmarkNotFoundError, LLMGenerationError
from bookmarks.data.repository import BookmarkRepository
from bookmarks.services.llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)


class BookmarkService:
    """Service for bookmark business logic operations."""

    def __init__(self):
        """Initialize the bookmark service."""
        self.repository = BookmarkRepository()

    def get_all_bookmarks(self) -> dict[str, dict]:
        """Get all bookmarks from the repository."""
        return self.repository.get_all()

    def get_bookmark_by_id(self, bookmark_id: str) -> dict | None:
        """
        Get a bookmark by ID.

        Args:
            bookmark_id: The bookmark ID to retrieve

        Returns:
            Bookmark data dictionary or None if not found
        """
        return self.repository.get_by_id(bookmark_id)

    def create_bookmark(
        self,
        url: str,
        title: str,
        description: str,
        tags: list[str],
        favorite: bool = False,
    ) -> tuple[str, dict]:
        """
        Create a new bookmark.

        Args:
            url: The bookmark URL
            title: The bookmark title
            description: The bookmark description
            tags: List of tags
            favorite: Whether the bookmark is a favorite

        Returns:
            Tuple of (bookmark_id, bookmark_data)
        """
        new_bookmark = {
            "url": url,
            "title": title,
            "description": description,
            "tags": tags,
            "favorite": favorite,
            "dateAdded": datetime.now(UTC).isoformat(),
        }

        # Generate ID and save
        new_id = self.repository.generate_new_id()
        self.repository.save(new_id, new_bookmark)

        logger.info(f"Created bookmark with ID: {new_id}")
        return new_id, new_bookmark

    def update_bookmark(
        self,
        bookmark_id: str,
        url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        favorite: bool | None = None,
    ) -> dict:
        """
        Update an existing bookmark.

        Args:
            bookmark_id: The bookmark ID to update
            url: New URL (optional)
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)
            favorite: New favorite status (optional)

        Returns:
            Updated bookmark data

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
        """
        bookmark = self.repository.get_by_id(bookmark_id)
        if not bookmark:
            raise BookmarkNotFoundError(bookmark_id)

        # Update fields if provided
        if url is not None:
            bookmark["url"] = url
        if title is not None:
            bookmark["title"] = title
        if description is not None:
            bookmark["description"] = description
        if tags is not None:
            bookmark["tags"] = tags
        if favorite is not None:
            bookmark["favorite"] = favorite

        self.repository.save(bookmark_id, bookmark)
        logger.info(f"Updated bookmark: {bookmark_id}")
        return bookmark

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark.

        Args:
            bookmark_id: The bookmark ID to delete

        Returns:
            True if deleted, False if not found
        """
        result = self.repository.delete(bookmark_id)
        if result:
            logger.info(f"Deleted bookmark: {bookmark_id}")
        else:
            logger.warning(f"Bookmark not found for deletion: {bookmark_id}")
        return result

    def toggle_favorite(self, bookmark_id: str) -> dict:
        """
        Toggle the favorite status of a bookmark.

        Args:
            bookmark_id: The bookmark ID to toggle

        Returns:
            Updated bookmark data

        Raises:
            BookmarkNotFoundError: If bookmark doesn't exist
        """
        bookmark = self.repository.get_by_id(bookmark_id)
        if not bookmark:
            raise BookmarkNotFoundError(bookmark_id)

        # Toggle favorite status
        bookmark["favorite"] = not bookmark.get("favorite", False)
        self.repository.save(bookmark_id, bookmark)

        logger.info(f"Toggled favorite for bookmark {bookmark_id}: {bookmark['favorite']}")
        return bookmark

    def generate_metadata(self, url: str) -> dict[str, str]:
        """
        Generate title and description for a URL using LLM.

        Args:
            url: The URL to generate metadata for

        Returns:
            Dictionary with 'title' and 'description' keys

        Raises:
            LLMGenerationError: If generation fails
        """
        try:
            logger.info(f"Generating metadata for URL: {url}")
            client = LLMClientFactory.create_client(
                provider=config.LLM_PROVIDER, content_format=config.LLM_CONTENT_FORMAT
            )
            data = client.generate_description(url)

            title = data.get("title", url)
            description = data.get("description", "")

            logger.info(f"Generated title: {title[:50]}...")
            logger.info(f"Generated description length: {len(description)} chars")

            return {"title": title, "description": description}

        except Exception as e:
            logger.error(f"Error generating metadata for {url}: {str(e)}", exc_info=True)
            raise LLMGenerationError(url=url, original_error=e) from e

    def create_bookmark_with_llm(
        self,
        url: str,
        tags: list[str] | None = None,
        favorite: bool = False,
    ) -> tuple[str, dict]:
        """
        Create a bookmark with LLM-generated title and description.

        Args:
            url: The bookmark URL
            tags: List of tags (defaults to ["unread"])
            favorite: Whether the bookmark is a favorite
            use_mcp: Whether to use MCP client

        Returns:
            Tuple of (bookmark_id, bookmark_data)

        Raises:
            LLMGenerationError: If metadata generation fails
        """
        if tags is None:
            tags = ["unread"]

        # Generate metadata
        metadata = self.generate_metadata(url)

        # Create bookmark
        return self.create_bookmark(
            url=url,
            title=metadata["title"],
            description=metadata["description"],
            tags=tags,
            favorite=favorite,
        )

    def get_all_tags(self, bookmarks: dict[str, dict] | None = None) -> dict[str, int]:
        """
        Get all unique tags with their counts, sorted by frequency.

        Args:
            bookmarks: Optional dictionary of bookmarks to analyze
                      (defaults to all bookmarks)

        Returns:
            Dictionary mapping tag names to their counts,
            sorted by frequency (descending) then alphabetically
        """
        if bookmarks is None:
            bookmarks = self.repository.get_all()

        tag_counts = {}
        for bookmark in bookmarks.values():
            for tag in bookmark.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count (descending), then alphabetically for ties
        return dict(sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower())))
