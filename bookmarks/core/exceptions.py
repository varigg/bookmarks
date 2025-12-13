#!/usr/bin/env python3
"""
Custom exceptions for the bookmark application.

This module defines the exception hierarchy for consistent error handling
across the application.
"""


class BookmarkError(Exception):
    """Base exception for all bookmark-related errors."""

    pass


class BookmarkNotFoundError(BookmarkError):
    """Raised when a requested bookmark does not exist."""

    def __init__(self, bookmark_id: str):
        self.bookmark_id = bookmark_id
        super().__init__(f"Bookmark with ID '{bookmark_id}' not found")


class BookmarkValidationError(BookmarkError):
    """Raised when bookmark data fails validation."""

    pass


class LLMGenerationError(BookmarkError):
    """Raised when LLM content generation fails."""

    def __init__(self, url: str, original_error: Exception):
        self.url = url
        self.original_error = original_error
        super().__init__(f"Failed to generate content for {url}: {original_error}")


class DataStorageError(BookmarkError):
    """Raised when reading or writing bookmark data fails."""

    pass
