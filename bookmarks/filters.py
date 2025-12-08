#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter state management for bookmark filtering.

This module provides a dataclass to manage filter state across routes.
"""

from dataclasses import dataclass
from typing import Optional

from bookmarks.utils import parse_tags


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
