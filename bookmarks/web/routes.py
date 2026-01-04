#!/usr/bin/env python3
"""Routes for the bookmark application."""

import logging
from typing import Any

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from bookmarks.core.exceptions import BookmarkNotFoundError, LLMGenerationError
from bookmarks.services.bookmark_service import BookmarkService
from bookmarks.web.filters import FilterState, apply_filters
from bookmarks.web.sorting import sort_bookmarks
from bookmarks.web.utils import parse_tags
from bookmarks.web.validation import (
    AutofillSchema,
    BookmarkCreateSchema,
    BookmarkUpdateSchema,
)

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


def _load_form_data(schema_cls):
    """Load form data into a Pydantic schema."""
    return schema_cls(**request.form)


def get_bookmark_service():
    """Get or create bookmark service instance in app context."""
    if "bookmark_service" not in g:
        g.bookmark_service = BookmarkService()
    return g.bookmark_service


@bp.app_context_processor
def inject_filter_params() -> dict[str, Any]:
    """Make filter parameters available to all templates."""
    filter_state = FilterState.from_request_args(request.args)
    return filter_state.to_dict()


@bp.route("/")
def index():
    """Redirect to bookmarks page."""
    return redirect(url_for(".bookmarks"))


@bp.route("/bookmarks")
def bookmarks() -> str:
    """
    Display bookmarks with optional filtering.
    """
    # Get all bookmarks
    all_bookmarks = get_bookmark_service().get_all_bookmarks()

    # Get filter state
    filter_state = FilterState.from_request_args(request.args)

    # Apply filters
    filtered_bookmarks = apply_filters(all_bookmarks, filter_state)

    # Apply sorting
    if filter_state.criteria:
        filtered_bookmarks = sort_bookmarks(filtered_bookmarks, filter_state.criteria)

    # Get tags from filtered bookmarks for progressive filtering
    available_tags = get_bookmark_service().get_all_tags(filtered_bookmarks)

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
    bookmark_data = get_bookmark_service().get_bookmark_by_id(id)
    if bookmark_data:
        filter_state = FilterState.from_request_args(request.args)
        return render_template(
            "bookmark.html", bookmark=bookmark_data, id=id, **filter_state.to_dict()
        )
    else:
        return "Bookmark not found", 404


@bp.route("/bookmarks/<path:id>/update", methods=["POST"])
def update_bookmark(id: str):
    """
    Updates the URL, title, description, and tags of a bookmark.
    """
    try:
        data = _load_form_data(BookmarkUpdateSchema)
    except Exception as e:
        return f"Invalid input: {str(e)}", 400

    # Update the bookmark using service
    try:
        get_bookmark_service().update_bookmark(
            bookmark_id=id,
            url=str(data.url) if data.url else None,  # Convert HttpUrl to string
            title=data.title,
            description=data.description,
            tags=data.tags,
        )
    except BookmarkNotFoundError:
        abort(404)

    # After update, redirect back to bookmarks list with filters preserved
    filter_state = FilterState.from_request_form(request.form)
    return redirect(url_for(".bookmarks", **filter_state.to_url_params()))


@bp.route("/bookmarks/new", methods=["GET", "POST"])
def new_bookmark():
    """
    Handles the creation of a new bookmark.
    """
    if request.method == "POST":
        try:
            data = _load_form_data(BookmarkCreateSchema)

            # Create the bookmark using service
            get_bookmark_service().create_bookmark(
                url=str(data.url),  # Convert HttpUrl to string
                title=data.title,
                description=data.description,
                tags=data.tags,
            )

            return redirect(url_for(".bookmarks"))
        except Exception as e:
            flash(f"Invalid input: {str(e)}", "error")
            return render_template("new_bookmark.html", **request.form)

    return render_template("new_bookmark.html")


@bp.route("/bookmarks/autofill", methods=["POST"])
def autofill_bookmark():
    """
    Generates title and description for a URL using LLM.
    """
    try:
        # Validate input data
        data = AutofillSchema(**request.form)  # type: ignore - pydantic dynamic typing
        url = str(data.url)  # Convert HttpUrl to string
    except Exception:
        return "Missing or invalid URL", 400

    logger.info(f"Autofill request for URL: {url}")

    try:
        # Generate metadata using service
        logger.info(f"Generating description for: {url}")
        metadata = get_bookmark_service().generate_metadata(url)

        # Safe handling of potentially None values
        title = metadata.get("title") or ""
        description = metadata.get("description", "")

        logger.info(f"Generated title: {title[:50] if title else 'N/A'}...")  # Log first 50 chars
        logger.info(f"Generated description length: {len(description)} chars")

        return render_template(
            "new_bookmark.html",
            url=url,
            title=title,
            description=description,
            tags="unread",  # Default tag
        )
    except LLMGenerationError as e:
        logger.error(f"Error generating description for {url}: {str(e)}", exc_info=True)
        flash(f"Error generating description: {str(e)}", "error")
        return render_template("new_bookmark.html", url=url)


@bp.route("/bookmarks/delete/<path:id>", methods=["POST"])
def delete_bookmark_route(id: str):
    """
    Route to delete a bookmark by ID.
    """
    if get_bookmark_service().delete_bookmark(id):
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

        # Create bookmark with LLM-generated metadata
        try:
            new_id, new_bookmark = get_bookmark_service().create_bookmark_with_llm(
                url=url, tags=tags, favorite=favorite
            )
        except LLMGenerationError as e:
            logger.error(f"API: Error generating description for {url}: {str(e)}")
            # Fall back to creating bookmark with URL as title
            new_id, new_bookmark = get_bookmark_service().create_bookmark(
                url=url,
                title=url,
                description=f"Error generating description: {str(e)}",
                tags=tags,
                favorite=favorite,
            )

        logger.info(f"API: Successfully created bookmark with ID: {new_id}")

        # Return success response
        return {"success": True, "bookmark": {"id": new_id, **new_bookmark}}, 201

    except Exception as e:
        logger.error(f"API: Unexpected error creating bookmark: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Internal server error: {str(e)}"}, 500


@bp.route("/bookmarks/<path:id>/favorite", methods=["POST"])
def toggle_favorite(id: str):
    """
    Toggle the favorite status of a bookmark.
    """
    try:
        get_bookmark_service().toggle_favorite(id)
    except BookmarkNotFoundError:
        flash("Bookmark not found.", "error")
        return redirect(url_for(".bookmarks"))

    # Preserve filters when redirecting
    filter_state = FilterState.from_request_form(request.form)

    return redirect(url_for(".bookmarks", **filter_state.to_url_params()))
