#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain models for the bookmarks application.

This module defines the core data structures used throughout the application.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Bookmark:
    """
    Represents a single bookmark with all its metadata.
    
    Attributes:
        url: The URL of the bookmarked page
        title: The title of the bookmark
        description: A description of the bookmarked content
        tags: List of tags for categorization
        dateAdded: ISO format timestamp of when bookmark was created
        favorite: Whether this bookmark is marked as favorite
    """
    url: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    dateAdded: str = ""  # ISO format timestamp
    favorite: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        """
        Create a Bookmark instance from a dictionary.
        
        Args:
            data: Dictionary containing bookmark data
            
        Returns:
            Bookmark instance with data from the dictionary
        """
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            dateAdded=data.get("dateAdded", ""),
            favorite=data.get("favorite", False),
        )

    def to_dict(self) -> dict:
        """
        Convert the Bookmark instance to a dictionary.
        
        Returns:
            Dictionary representation of the bookmark
        """
        return asdict(self)

    @classmethod
    def create_new(
        cls,
        url: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        favorite: bool = False,
    ) -> "Bookmark":
        """
        Factory method to create a new bookmark with current timestamp.
        
        Args:
            url: The URL of the bookmarked page
            title: The title of the bookmark
            description: A description of the bookmarked content
            tags: Optional list of tags (defaults to empty list)
            favorite: Whether this bookmark is marked as favorite (defaults to False)
            
        Returns:
            New Bookmark instance with dateAdded set to current time
        """
        from datetime import timezone
        
        return cls(
            url=url,
            title=title,
            description=description,
            tags=tags or [],
            dateAdded=datetime.now(timezone.utc).isoformat(),
            favorite=favorite,
        )

    def update(
        self,
        url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        favorite: Optional[bool] = None,
    ) -> None:
        """
        Update bookmark fields with new values.
        
        Args:
            url: New URL (if provided)
            title: New title (if provided)
            description: New description (if provided)
            tags: New tags list (if provided)
            favorite: New favorite status (if provided)
        """
        if url is not None:
            self.url = url
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if tags is not None:
            self.tags = tags
        if favorite is not None:
            self.favorite = favorite

    def toggle_favorite(self) -> None:
        """Toggle the favorite status of this bookmark."""
        self.favorite = not self.favorite
