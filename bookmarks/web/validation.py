#!/usr/bin/env python3
"""
Input validation schemas using Pydantic.

This module defines validation models for bookmark data.
"""

from pydantic import BaseModel, Field, HttpUrl, field_validator

from bookmarks.web.utils import parse_tags


class BookmarkCreateSchema(BaseModel):
    """Schema for creating a new bookmark."""

    url: HttpUrl = Field(..., description="The URL of the bookmark")
    title: str = Field(..., min_length=1, max_length=500, description="The title of the bookmark")
    description: str = Field("", max_length=2000, description="The description of the bookmark")
    tags: list[str] = Field(
        default_factory=list, description="Comma-separated tags or list of tags"
    )

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags_field(cls, v):
        """Convert comma-separated string to list of tags."""
        if isinstance(v, str):
            return parse_tags(v)
        return v if v is not None else []


class BookmarkUpdateSchema(BaseModel):
    """Schema for updating an existing bookmark."""

    url: HttpUrl | None = Field(None, description="The URL of the bookmark")
    title: str | None = Field(
        None, min_length=1, max_length=500, description="The title of the bookmark"
    )
    description: str | None = Field(
        None, max_length=2000, description="The description of the bookmark"
    )
    tags: list[str] | None = Field(None, description="Comma-separated tags or list of tags")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags_field(cls, v):
        """Convert comma-separated string to list of tags."""
        if isinstance(v, str):
            return parse_tags(v)
        return v


class AutofillSchema(BaseModel):
    """Schema for autofill requests."""

    url: HttpUrl = Field(..., description="The URL to generate metadata for")
