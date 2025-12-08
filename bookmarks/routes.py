#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Routes for the bookmark application."""

import logging
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from bookmarks.filters import FilterState
from bookmarks.model import delete_bookmark, get_bookmark, get_bookmarks, save_bookmark
from bookmarks.repository import BookmarkRepository
from bookmarks.services import PerplexityClientFactory
from bookmarks.utils import parse_tags

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


@bp.app_context_processor
def inject_filter_params() -> dict[str, Any]:
    """Make filter parameters available to all templates."""
    filter_state = FilterState.from_request_args(request.args)
    return filter_state.to_dict()


def _sort_bookmarks(bookmarks: dict[str, dict], criteria: str) -> dict[str, dict]:
    """Sorts bookmarks based on the given criteria."""
    if criteria == "newest":
        return dict(
            sorted(
                bookmarks.items(),
                key=lambda item: item[1].get("dateAdded", ""),
                reverse=True,
            )
        )
    elif criteria == "oldest":
        return dict(
            sorted(bookmarks.items(), key=lambda item: item[1].get("dateAdded", ""))
        )
    elif criteria == "a-z":
        return dict(
            sorted(
                bookmarks.items(), key=lambda item: (item[1].get("title") or "").lower()
            )
        )
    elif criteria == "z-a":
        return dict(
            sorted(
                bookmarks.items(),
                key=lambda item: (item[1].get("title") or "").lower(),
                reverse=True,
            )
        )
    elif criteria == "favorites":
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


def _get_all_tags(bookmarks: dict[str, dict] | None = None) -> dict[str, int]:
    """Returns list of all unique tags across bookmarks with counts, sorted by frequency (most used first)."""
    if bookmarks is None:
        bookmarks = get_bookmarks()

    tag_counts = {}
    for bookmark in bookmarks.values():
        for tag in bookmark.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    # Sort by count (descending), then alphabetically for ties
    return dict(sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower())))


def _apply_tag_filter_and(bookmarks: dict[str, dict], filter_tags: list[str]) -> dict[str, dict]:
    """Filter bookmarks by tags with AND logic - bookmark must have ALL selected tags."""
    if not filter_tags:
        return bookmarks

    return {
        id: bookmark
        for id, bookmark in bookmarks.items()
        if all(tag in bookmark.get("tags", []) for tag in filter_tags)
    }


def _build_redirect_url(endpoint=".bookmarks", **kwargs):
    """Builds a redirect URL with optional query parameters."""
    # Filter out None values
    params = {k: v for k, v in kwargs.items() if v is not None}
    return url_for(endpoint, **params)


@bp.route("/")
def index() -> Response:
    return redirect(url_for(".bookmarks"))


@bp.route("/bookmarks")
def bookmarks() -> str:
    """
    Display bookmarks with optional filtering.
    """
    # Get all bookmarks
    all_bookmarks = get_bookmarks()

    # Get filter state
    filter_state = FilterState.from_request_args(request.args)

    # Apply tag filter with AND logic
    filtered_bookmarks = all_bookmarks
    if filter_state.tags:
        filtered_bookmarks = _apply_tag_filter_and(filtered_bookmarks, filter_state.tags)

    # Apply favorite filter
    if filter_state.favorite:
        filtered_bookmarks = {
            id: bookmark
            for id, bookmark in filtered_bookmarks.items()
            if bookmark.get("favorite", False)
        }

    # Apply description filter
    if filter_state.description:
        filtered_bookmarks = {
            id: bookmark
            for id, bookmark in filtered_bookmarks.items()
            if filter_state.description.lower() in (bookmark.get("description") or "").lower()
        }

    # Apply sorting
    if filter_state.criteria:
        filtered_bookmarks = _sort_bookmarks(filtered_bookmarks, filter_state.criteria)

    # Get tags from filtered bookmarks for progressive filtering
    available_tags = _get_all_tags(filtered_bookmarks)

    return render_template(
        "bookmarks.html",
        bookmarks=filtered_bookmarks,
        all_tags=available_tags,
        **filter_state.to_dict(),  # Unpack filter state for template
    )


@bp.route("/bookmarks/<path:id>")
def bookmark(id: str) -> str | tuple[str, int]:
    """
    Returns the bookmark data for a given id.
    """
    bookmark = get_bookmark(id)
    if bookmark:
        filter_state = FilterState.from_request_args(request.args)
        return render_template("bookmark.html", bookmark=bookmark, id=id, **filter_state.to_dict())
    else:
        return "Bookmark not found", 404


@bp.route("/bookmarks/<path:id>/update", methods=["POST"])
def update_bookmark(id: str) -> Response | tuple[str, int]:
    """
    Updates the URL, title, description, and tags of a bookmark.
    """
    bookmark = get_bookmark(id)
    if not bookmark:
        return "Bookmark not found", 404

    # Get updated data from the form
    new_url = request.form.get("url")
    new_title = request.form.get("title")
    new_description = request.form.get("description")
    new_tags = parse_tags(request.form.get("tags"))

    # Update the bookmark
    bookmark["url"] = new_url
    bookmark["title"] = new_title
    bookmark["description"] = new_description
    bookmark["tags"] = new_tags
    save_bookmark(id, bookmark)  # Save the updated bookmark

    # Get filter state from form hidden fields
    filter_state = FilterState.from_request_form(request.form)

    # Build the redirect URL with query parameters
    redirect_url = url_for(".bookmarks", **filter_state.to_url_params())

    return redirect(redirect_url)


@bp.route("/bookmarks/new", methods=["GET", "POST"])
def new_bookmark() -> Response | str:
    """
    Handles the creation of a new bookmark.
    """
    if request.method == "POST":
        # Get data from the form
        new_url = request.form.get("url")
        new_title = request.form.get("title")
        new_description = request.form.get("description")
        new_tags = parse_tags(request.form.get("tags"))

        # Create a new bookmark object
        new_bookmark = {
            "url": new_url,
            "title": new_title,
            "description": new_description,
            "tags": new_tags,
            "dateAdded": datetime.now(
                timezone.utc
            ).isoformat(),  # Add current timestamp
        }

        # Save the new bookmark
        repo = BookmarkRepository()
        new_id = repo.generate_new_id()
        save_bookmark(new_id, new_bookmark)

        return redirect(url_for(".bookmarks"))

    return render_template("new_bookmark.html")


@bp.route("/bookmarks/autofill", methods=["POST"])
def autofill_bookmark() -> Response:
    """
    Generates title and description for a URL using LLM.
    """
    url = request.form.get("url")
    logger.info(f"Autofill request for URL: {url}")

    if not url:
        logger.warning("Autofill request with no URL")
        flash("Please enter a URL.", "error")
        return redirect(url_for(".bookmarks"))

    try:
        # Create client (defaults to direct API, no markdown for speed)
        logger.info("Creating Perplexity client...")
        client = PerplexityClientFactory.create_client()

        logger.info(f"Generating description for: {url}")
        data = client.generate_description(url)

        # Safe handling of potentially None values
        title = data.get('title') or ''
        description = data.get('description', '')
        
        logger.info(
            f"Generated title: {title[:50] if title else 'N/A'}..."
        )  # Log first 50 chars
        logger.info(
            f"Generated description length: {len(description)} chars"
        )

        return render_template(
            "new_bookmark.html",
            url=url,
            title=title,
            description=description,
            tags="unread",  # Default tag
        )
    except Exception as e:
        logger.error(f"Error generating description for {url}: {str(e)}", exc_info=True)
        flash(f"Error generating description: {str(e)}", "error")
        return render_template("new_bookmark.html", url=url)


@bp.route("/bookmarks/delete/<path:id>", methods=["POST"])
def delete_bookmark_route(id: str) -> Response:
    """
    Route to delete a bookmark by ID.
    """
    if delete_bookmark(id):
        flash("Bookmark deleted successfully.", "success")
    else:
        flash("Bookmark not found.", "error")

    # Get filter state from form hidden fields
    filter_state = FilterState.from_request_form(request.form)

    return redirect(url_for(".bookmarks", **filter_state.to_url_params()))


@bp.route("/api/bookmarks", methods=["POST"])
def api_create_bookmark() -> tuple[dict[str, Any], int]:
    """
    API endpoint to create a bookmark from a URL with auto-generated title and description.

    Request JSON:
        {
            "url": "https://example.com",
            "tags": ["optional", "tags"],  // Optional
            "favorite": false  // Optional
        }

    Response JSON:
        {
            "success": true,
            "bookmark": {
                "id": "123",
                "url": "https://example.com",
                "title": "Generated Title",
                "description": "Generated description...",
                "tags": ["optional", "tags"],
                "favorite": false,
                "dateAdded": "2025-12-07T..."
            }
        }

    Error Response:
        {
            "success": false,
            "error": "Error message"
        }
    """
    try:
        # Parse JSON request
        data = request.get_json()
        if not data:
            return {"success": False, "error": "No JSON data provided"}, 400

        url = data.get("url")
        if not url:
            return {"success": False, "error": "URL is required"}, 400

        # Optional parameters
        tags = data.get("tags", ["unread"])
        if isinstance(tags, str):
            tags = parse_tags(tags)
        favorite = data.get("favorite", False)

        logger.info(f"API: Creating bookmark for URL: {url}")

        # Generate title and description using LLM
        try:
            client = PerplexityClientFactory.create_client()
            generated_data = client.generate_description(url)
            title = generated_data.get("title", url)
            description = generated_data.get("description", "")
        except Exception as e:
            logger.error(f"API: Error generating description for {url}: {str(e)}")
            # Fall back to URL as title if generation fails
            title = url
            description = f"Error generating description: {str(e)}"

        # Create bookmark object
        new_bookmark = {
            "url": url,
            "title": title,
            "description": description,
            "tags": tags,
            "favorite": favorite,
            "dateAdded": datetime.now(timezone.utc).isoformat(),
        }

        # Save bookmark
        repo = BookmarkRepository()
        new_id = repo.generate_new_id()
        save_bookmark(new_id, new_bookmark)

        logger.info(f"API: Successfully created bookmark with ID: {new_id}")

        # Return success response
        return {"success": True, "bookmark": {"id": new_id, **new_bookmark}}, 201

    except Exception as e:
        logger.error(
            f"API: Unexpected error creating bookmark: {str(e)}", exc_info=True
        )
        return {"success": False, "error": f"Internal server error: {str(e)}"}, 500


@bp.route("/bookmarks/<path:id>/favorite", methods=["POST"])
def toggle_favorite(id: str) -> Response:
    """
    Toggle the favorite status of a bookmark.
    """
    bookmark = get_bookmark(id)
    if not bookmark:
        flash("Bookmark not found.", "error")
        return redirect(url_for(".bookmarks"))

    # Toggle favorite status
    bookmark["favorite"] = not bookmark.get("favorite", False)
    save_bookmark(id, bookmark)

    # Preserve filters when redirecting
    filter_state = FilterState.from_request_form(request.form)

    return redirect(url_for(".bookmarks", **filter_state.to_url_params()))
