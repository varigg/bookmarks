#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository pattern for bookmark data access.

This module provides thread-safe bookmark data access without global state.
Each instance maintains its own bookmark collection loaded from the data source.
"""

from typing import Optional, Union

from bookmarks.core.domain import Bookmark
from bookmarks.core.exceptions import BookmarkNotFoundError, DataStorageError
from bookmarks.data.datafile import get_data, write_data


class BookmarkRepository:
    """
    Repository for bookmark data access.
    
    Provides CRUD operations for bookmarks with encapsulated state management.
    Thread-safe when each request gets its own instance from application context.
    """

    def __init__(self):
        """Initialize repository and load bookmarks from data source."""
        self._bookmarks: dict[str, dict] = {}
        self._load_bookmarks()

    def _load_bookmarks(self) -> None:
        """Load bookmarks from data source into memory."""
        try:
            data = get_data()
            self._bookmarks = {str(i): bookmark for i, bookmark in enumerate(data)}
        except Exception as e:
            raise DataStorageError(f"Failed to load bookmarks: {e}") from e

    def reload(self) -> None:
        """Reload bookmarks from data source (useful for testing)."""
        self._bookmarks.clear()
        self._load_bookmarks()

    def get_all(self) -> dict[str, dict]:
        """
        Get all bookmarks as dictionaries.
        
        Returns:
            Dictionary mapping bookmark IDs to bookmark data dictionaries.
        """
        return self._bookmarks.copy()

    def get_all_as_objects(self) -> dict[str, Bookmark]:
        """
        Get all bookmarks as Bookmark objects.
        
        Returns:
            Dictionary mapping bookmark IDs to Bookmark instances.
        """
        return {
            bookmark_id: Bookmark.from_dict(data)
            for bookmark_id, data in self._bookmarks.items()
        }

    def get_by_id(self, bookmark_id: str) -> Optional[dict]:
        """
        Get a single bookmark by ID as a dictionary.
        
        Args:
            bookmark_id: The bookmark ID to retrieve.
            
        Returns:
            Bookmark dictionary or None if not found.
        """
        return self._bookmarks.get(bookmark_id)

    def get_by_id_as_object(self, bookmark_id: str) -> Optional[Bookmark]:
        """
        Get a single bookmark by ID as a Bookmark object.
        
        Args:
            bookmark_id: The bookmark ID to retrieve.
            
        Returns:
            Bookmark instance or None if not found.
        """
        data = self._bookmarks.get(bookmark_id)
        return Bookmark.from_dict(data) if data else None

    def get_by_id_or_raise(self, bookmark_id: str) -> dict:
        """
        Get a single bookmark by ID, raising exception if not found.
        
        Args:
            bookmark_id: The bookmark ID to retrieve.
            
        Returns:
            Bookmark dictionary.
            
        Raises:
            BookmarkNotFoundError: If bookmark with given ID doesn't exist.
        """
        bookmark = self.get_by_id(bookmark_id)
        if bookmark is None:
            raise BookmarkNotFoundError(bookmark_id)
        return bookmark

    def save(self, bookmark_id: str, bookmark: Union[dict, Bookmark]) -> None:
        """
        Save or update a bookmark.
        
        Args:
            bookmark_id: The ID to save the bookmark under.
            bookmark: The bookmark data (dictionary or Bookmark instance).
            
        Raises:
            DataStorageError: If saving fails.
        """
        # Ensure ID is string
        bookmark_id = str(bookmark_id)
        
        # Convert Bookmark to dict if needed
        bookmark_dict = bookmark.to_dict() if isinstance(bookmark, Bookmark) else bookmark
        
        # Update in-memory store
        self._bookmarks[bookmark_id] = bookmark_dict
        
        # Persist to storage
        try:
            write_data(self._bookmarks.values())
        except Exception as e:
            raise DataStorageError(f"Failed to save bookmark {bookmark_id}: {e}") from e

    def delete(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark by ID.
        
        Args:
            bookmark_id: The ID of the bookmark to delete.
            
        Returns:
            True if deleted, False if not found.
            
        Raises:
            DataStorageError: If deletion fails during persistence.
        """
        bookmark_id = str(bookmark_id)
        
        if bookmark_id not in self._bookmarks:
            return False
        
        # Remove from in-memory store
        del self._bookmarks[bookmark_id]
        
        # Persist to storage
        try:
            write_data(self._bookmarks.values())
        except Exception as e:
            raise DataStorageError(f"Failed to delete bookmark {bookmark_id}: {e}") from e
        
        return True

    def generate_new_id(self) -> str:
        """
        Generate the next available bookmark ID.
        
        Returns:
            String ID for a new bookmark.
        """
        current_ids = [int(bid) for bid in self._bookmarks.keys() if bid.isdigit()]
        return str(max(current_ids, default=-1) + 1)

    def exists(self, bookmark_id: str) -> bool:
        """
        Check if a bookmark exists.
        
        Args:
            bookmark_id: The bookmark ID to check.
            
        Returns:
            True if bookmark exists, False otherwise.
        """
        return bookmark_id in self._bookmarks

    def count(self) -> int:
        """
        Get the total number of bookmarks.
        
        Returns:
            Count of bookmarks.
        """
        return len(self._bookmarks)
