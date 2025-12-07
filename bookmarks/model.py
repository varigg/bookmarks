#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy model interface for bookmark operations.

DEPRECATED: This module maintains backward compatibility with existing code.
New code should use BookmarkRepository directly from bookmarks.repository.

This will be phased out in Phase 4 of the refactoring.
"""

from bookmarks.repository import BookmarkRepository

# Global repository instance for backward compatibility
# TODO: Remove in Phase 4 when routes use Flask application context
_repository = None


def _get_repository() -> BookmarkRepository:
    """Get or create the global repository instance."""
    global _repository
    if _repository is None:
        _repository = BookmarkRepository()
    return _repository


def init_bookmarks():
    """
    Initialize or reload bookmarks from data source.
    
    DEPRECATED: Maintained for test compatibility.
    """
    global _repository
    _repository = BookmarkRepository()


def get_bookmarks():
    """
    Returns the bookmarks data.
    
    Returns:
        Dictionary mapping bookmark IDs to bookmark dictionaries.
    """
    return _get_repository().get_all()


def get_bookmark(id):
    """
    Returns the bookmark data for a given ID.
    
    Args:
        id: The bookmark ID to retrieve.
        
    Returns:
        Bookmark dictionary or None if not found.
    """
    return _get_repository().get_by_id(id)


def save_bookmark(id, bookmark):
    """
    Saves the bookmark data to the bookmarks.js file.
    
    Args:
        id: The bookmark ID.
        bookmark: The bookmark data dictionary.
    """
    _get_repository().save(id, bookmark)


def delete_bookmark(id):
    """
    Deletes the bookmark with the given ID.
    
    Args:
        id: The bookmark ID to delete.
        
    Returns:
        True if deleted, False if not found.
    """
    return _get_repository().delete(id)
