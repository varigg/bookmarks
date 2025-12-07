#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Routes for the bookmark application."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)

from bookmarks.model import delete_bookmark, get_bookmark, get_bookmarks, save_bookmark
from bookmarks.services import PerplexityClientFactory

bp = Blueprint("main", __name__)


@bp.app_context_processor
def inject_filter_params():
    """Make filter parameters available to all templates."""
    return _get_filter_context()


def _parse_tags(tags_string):
    """Parses a comma-separated string of tags into a list."""
    if not tags_string:
        return []
    return [tag.strip() for tag in tags_string.split(",") if tag.strip()]


def _sort_bookmarks(bookmarks, criteria):
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


def _get_all_tags(bookmarks=None):
    """Returns list of all unique tags across bookmarks with counts, sorted by frequency (most used first)."""
    if bookmarks is None:
        bookmarks = get_bookmarks()

    tag_counts = {}
    for bookmark in bookmarks.values():
        for tag in bookmark.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    # Sort by count (descending), then alphabetically for ties
    return dict(sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower())))


def _parse_tag_filter(tag_param):
    """Parses tag filter parameter into list of tags."""
    if not tag_param:
        return []
    # Support comma-separated tags
    return [tag.strip() for tag in tag_param.split(",") if tag.strip()]


def _apply_tag_filter_and(bookmarks, filter_tags):
    """Filter bookmarks by tags with AND logic - bookmark must have ALL selected tags."""
    if not filter_tags:
        return bookmarks

    return {
        id: bookmark
        for id, bookmark in bookmarks.items()
        if all(tag in bookmark.get("tags", []) for tag in filter_tags)
    }


def _get_filter_context():
    """Extracts filter parameters from request args and returns as dict."""
    tag_param = request.args.get("tag")
    filter_tags = _parse_tag_filter(tag_param)

    return {
        "filter_tags": filter_tags,  # List of tags
        "filter_tag": tag_param,  # Original string for URLs
        "filter_criteria": request.args.get("criteria"),
        "filter_description": request.args.get("description"),
        "filter_favorite": request.args.get("favorite"),  # Favorite filter
    }


def _build_redirect_url(endpoint=".bookmarks", **kwargs):
    """Builds a redirect URL with optional query parameters."""
    # Filter out None values
    params = {k: v for k, v in kwargs.items() if v is not None}
    return url_for(endpoint, **params)


@bp.route("/")
def index():
    return redirect(url_for(".bookmarks"))


@bp.route("/bookmarks")
def bookmarks():
    """
    Display bookmarks with optional filtering.
    """
    # Get all bookmarks
    all_bookmarks = get_bookmarks()

    # Get filter context
    filters = _get_filter_context()
    filter_tags = filters["filter_tags"]
    filter_criteria = filters["filter_criteria"]
    filter_description = filters["filter_description"]
    filter_favorite = filters["filter_favorite"]

    # Apply tag filter with AND logic
    filtered_bookmarks = all_bookmarks
    if filter_tags:
        filtered_bookmarks = _apply_tag_filter_and(filtered_bookmarks, filter_tags)

    # Apply favorite filter
    if filter_favorite:
        filtered_bookmarks = {
            id: bookmark
            for id, bookmark in filtered_bookmarks.items()
            if bookmark.get("favorite", False)
        }

    # Apply description filter
    if filter_description:
        filtered_bookmarks = {
            id: bookmark
            for id, bookmark in filtered_bookmarks.items()
            if filter_description.lower() in (bookmark.get("description") or "").lower()
        }

    # Apply sorting
    if filter_criteria:
        filtered_bookmarks = _sort_bookmarks(filtered_bookmarks, filter_criteria)

    # Get tags from filtered bookmarks for progressive filtering
    available_tags = _get_all_tags(filtered_bookmarks)

    return render_template(
        "bookmarks.html",
        bookmarks=filtered_bookmarks,
        all_tags=available_tags,
        **filters,  # Unpack all filter variables
    )


@bp.route("/bookmarks/<path:id>")
def bookmark(id):
    """
    Returns the bookmark data for a given id.
    """
    bookmark = get_bookmark(id)
    if bookmark:
        filters = _get_filter_context()
        return render_template("bookmark.html", bookmark=bookmark, id=id, **filters)
    else:
        return "Bookmark not found", 404


@bp.route("/bookmarks/<path:id>/update", methods=["POST"])
def update_bookmark(id):
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
    new_tags = _parse_tags(request.form.get("tags"))

    # Update the bookmark
    bookmark["url"] = new_url
    bookmark["title"] = new_title
    bookmark["description"] = new_description
    bookmark["tags"] = new_tags
    save_bookmark(id, bookmark)  # Save the updated bookmark

    tag = request.form.get("filter_tag", None)
    criteria = request.form.get("filter_criteria", None)
    description = request.form.get("filter_description", None)

    # Build the redirect URL with query parameters if they exist
    redirect_url = _build_redirect_url(
        ".bookmarks", tag=tag, criteria=criteria, description=description
    )

    return redirect(redirect_url)


@bp.route("/bookmarks/new", methods=["GET", "POST"])
def new_bookmark():
    """
    Handles the creation of a new bookmark.
    """
    if request.method == "POST":
        # Get data from the form
        # Get data from the form
        new_url = request.form.get("url")
        new_title = request.form.get("title")
        new_description = request.form.get("description")
        new_tags = _parse_tags(request.form.get("tags"))

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
        bookmarks = get_bookmarks()
        # Generate a new ID based on the max integer ID + 1 to avoid collisions
        # Default to -1 so the first ID is 0
        current_ids = [int(bid) for bid in bookmarks.keys() if bid.isdigit()]
        new_id = str(max(current_ids, default=-1) + 1)
        save_bookmark(new_id, new_bookmark)

        return redirect(url_for(".bookmarks"))

    return render_template("new_bookmark.html")


@bp.route("/bookmarks/autofill", methods=["POST"])
def autofill_bookmark():
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
def delete_bookmark_route(id):
    """
    Route to delete a bookmark by ID.
    """
    if delete_bookmark(id):
        flash("Bookmark deleted successfully.", "success")
    else:
        flash("Bookmark not found.", "error")

    tag = request.form.get("filter_tag", None)
    criteria = request.form.get("filter_criteria", None)
    description = request.form.get("filter_description", None)

    return redirect(
        _build_redirect_url(
            ".bookmarks", tag=tag, criteria=criteria, description=description
        )
    )


@bp.route("/api/bookmarks", methods=["POST"])
def api_create_bookmark():
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
            tags = _parse_tags(tags)
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
        bookmarks = get_bookmarks()
        current_ids = [int(bid) for bid in bookmarks.keys() if bid.isdigit()]
        new_id = str(max(current_ids, default=-1) + 1)
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
def toggle_favorite(id):
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
    tag = request.form.get("filter_tag")
    criteria = request.form.get("filter_criteria")
    description = request.form.get("filter_description")
    favorite = request.form.get("filter_favorite")

    return redirect(
        _build_redirect_url(
            ".bookmarks",
            tag=tag,
            criteria=criteria,
            description=description,
            favorite=favorite,
        )
    )
