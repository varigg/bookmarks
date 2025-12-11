#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for bookmark operations.

This module contains shared utility functions used across the application.
"""


def parse_tags(tags_input: str | None) -> list[str]:
    """
    Parse comma-separated tag string into a list of tags.

    Args:
        tags_input: Comma-separated string of tags, or None.

    Returns:
        List of trimmed, non-empty tag strings.

    Examples:
        >>> parse_tags("python, flask, web")
        ['python', 'flask', 'web']
        >>> parse_tags("")
        []
        >>> parse_tags(None)
        []
    """
    if not tags_input:
        return []
    return [tag.strip() for tag in tags_input.split(",") if tag.strip()]
