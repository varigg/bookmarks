#!/usr/bin/env python3
"""Sorting utilities for bookmarks."""

from enum import Enum


class SortCriteria(str, Enum):
    """Available sorting criteria for bookmarks."""

    NEWEST = "newest"
    OLDEST = "oldest"
    ALPHABETICAL_AZ = "a-z"
    ALPHABETICAL_ZA = "z-a"
    FAVORITES_FIRST = "favorites"


def sort_bookmarks(bookmarks: dict[str, dict], criteria: str | SortCriteria) -> dict[str, dict]:
    """
    Sort bookmarks based on the given criteria.

    Args:
        bookmarks: Dictionary of bookmarks to sort
        criteria: Sorting criteria (SortCriteria enum or string)

    Returns:
        Sorted dictionary of bookmarks
    """
    # Convert string to enum if needed
    if isinstance(criteria, str):
        try:
            criteria = SortCriteria(criteria)
        except ValueError:
            # Invalid criteria, return unsorted
            return bookmarks

    if criteria == SortCriteria.NEWEST:
        return dict(
            sorted(
                bookmarks.items(),
                key=lambda item: item[1].get("dateAdded", ""),
                reverse=True,
            )
        )
    elif criteria == SortCriteria.OLDEST:
        return dict(sorted(bookmarks.items(), key=lambda item: item[1].get("dateAdded", "")))
    elif criteria == SortCriteria.ALPHABETICAL_AZ:
        return dict(
            sorted(bookmarks.items(), key=lambda item: (item[1].get("title") or "").lower())
        )
    elif criteria == SortCriteria.ALPHABETICAL_ZA:
        return dict(
            sorted(
                bookmarks.items(),
                key=lambda item: (item[1].get("title") or "").lower(),
                reverse=True,
            )
        )
    elif criteria == SortCriteria.FAVORITES_FIRST:
        return dict(
            sorted(
                bookmarks.items(),
                key=lambda item: (
                    not item[1].get("favorite", False),
                    item[1].get("dateAdded", ""),
                ),
                reverse=True,
            )
        )

    return bookmarks
