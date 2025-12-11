#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter state management for bookmark filtering.

This module provides a dataclass to manage filter state across routes.
"""

from dataclasses import dataclass
from typing import Optional

from bookmarks.web.utils import parse_tags


@dataclass
class FilterState:
    """
    Represents the current filter state for bookmarks.

    Attributes:
        tags: List of tag strings to filter by
        tag_string: Original comma-separated tag string (for URLs)
        criteria: Sorting criteria (newest, oldest, a-z, z-a, favorites)
        description: Text to search for in descriptions
        favorite: Whether to filter favorites only
    """

    tags: list[str]
    tag_string: Optional[str]
    criteria: Optional[str]
    description: Optional[str]
    favorite: Optional[str]

    @classmethod
    def from_request_args(cls, args) -> "FilterState":
        """
        Extract filter state from Flask request.args.

        Args:
            args: Flask request.args object

        Returns:
            FilterState instance with extracted values
        """
        tag_param = args.get("tag")
        return cls(
            tags=parse_tags(tag_param),
            tag_string=tag_param,
            criteria=args.get("criteria"),
            description=args.get("description"),
            favorite=args.get("favorite"),
        )

    @classmethod
    def from_request_form(cls, form) -> "FilterState":
        """
        Extract filter state from Flask request.form (hidden fields).

        Args:
            form: Flask request.form object

        Returns:
            FilterState instance with extracted values
        """
        tag_param = form.get("filter_tag")
        return cls(
            tags=parse_tags(tag_param),
            tag_string=tag_param,
            criteria=form.get("filter_criteria"),
            description=form.get("filter_description"),
            favorite=form.get("filter_favorite"),
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for template context.

        Returns:
            Dictionary with filter_ prefixed keys for templates
        """
        return {
            "filter_tags": self.tags,
            "filter_tag": self.tag_string,
            "filter_criteria": self.criteria,
            "filter_description": self.description,
            "filter_favorite": self.favorite,
        }

    def to_url_params(self) -> dict:
        """
        Convert to URL parameters, excluding None values.

        Returns:
            Dictionary suitable for url_for(**params)
        """
        params = {
            "tag": self.tag_string,
            "criteria": self.criteria,
            "description": self.description,
            "favorite": self.favorite,
        }
        # Filter out None values
        return {k: v for k, v in params.items() if v is not None}


def apply_tag_filter(
    bookmarks: dict[str, dict], filter_tags: list[str]
) -> dict[str, dict]:
    """
    Filter bookmarks by tags with AND logic.

    Bookmark must have ALL selected tags to be included.

    Args:
        bookmarks: Dictionary of bookmarks to filter
        filter_tags: List of tags that bookmarks must have

    Returns:
        Filtered dictionary of bookmarks
    """
    if not filter_tags:
        return bookmarks

    return {
        id: bookmark
        for id, bookmark in bookmarks.items()
        if all(tag in bookmark.get("tags", []) for tag in filter_tags)
    }


def apply_favorite_filter(bookmarks: dict[str, dict]) -> dict[str, dict]:
    """
    Filter bookmarks to only show favorites.

    Args:
        bookmarks: Dictionary of bookmarks to filter

    Returns:
        Filtered dictionary of bookmarks (only favorites)
    """
    return {
        id: bookmark
        for id, bookmark in bookmarks.items()
        if bookmark.get("favorite", False)
    }


def apply_description_filter(
    bookmarks: dict[str, dict], search_text: str
) -> dict[str, dict]:
    """
    Filter bookmarks by description text (case-insensitive).

    Args:
        bookmarks: Dictionary of bookmarks to filter
        search_text: Text to search for in descriptions

    Returns:
        Filtered dictionary of bookmarks
    """
    if not search_text:
        return bookmarks

    search_lower = search_text.lower()
    return {
        id: bookmark
        for id, bookmark in bookmarks.items()
        if search_lower in (bookmark.get("description") or "").lower()
    }


def apply_filters(
    bookmarks: dict[str, dict], filter_state: FilterState
) -> dict[str, dict]:
    """
    Apply all filters from a FilterState to bookmarks.

    Args:
        bookmarks: Dictionary of bookmarks to filter
        filter_state: FilterState containing all filter criteria

    Returns:
        Filtered dictionary of bookmarks
    """
    filtered = bookmarks

    # Apply tag filter (AND logic)
    if filter_state.tags:
        filtered = apply_tag_filter(filtered, filter_state.tags)

    # Apply favorite filter
    if filter_state.favorite:
        filtered = apply_favorite_filter(filtered)

    # Apply description filter
    if filter_state.description:
        filtered = apply_description_filter(filtered, filter_state.description)

    return filtered
