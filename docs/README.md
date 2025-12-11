# Bookmark Management Application - Documentation

A self-hosted Flask web application for managing bookmarks with LLM-powered automatic enrichment.

## Overview

This application is designed to run on your desktop or home network server, providing a personal bookmark management system that automatically generates titles and descriptions for your saved URLs.

### How It Works

1. **Self-hosted** - Run on your desktop or home server (no cloud service needed)
2. **Easy bookmarking** - Use browser extensions, iOS shortcuts, or the web interface
3. **Auto-enrichment** - Send a URL, get back a bookmark with title and description automatically generated
4. **Manual refinement** - Edit details as needed through the web interface

**Key benefit**: You don't write descriptions. Just send URLs, and the LLM service handles the rest.

## Quick Links

### Getting Started

- **[Main Project README](../README.md)** - Installation and quick start
- **[Browser Extension](../browser-extension/README.md)** - Firefox/Chrome one-click bookmarking
- **[iOS Shortcuts](IOS_SHORTCUTS.md)** - Share from Safari and iOS apps
- **[Deployment Guide](DEPLOYMENT.md)** - Running on your home server
- **[LLM Configuration Guide](LLM_CONFIGURATION.md)** - Complete guide to LLM service configuration

### User Guides

- **[Adding Bookmarks](ADDING_BOOKMARKS.md)** - How to add bookmarks (web UI, extensions, bulk import)
- **[LLM Quickstart](QUICKSTART_LLM.md)** - Quick start for LLM features
- **[MCP Integration Guide](MCP_GUIDE.md)** - Model Context Protocol setup and usage
- **[MarkItDown Comparison](MARKITDOWN_COMPARISON.md)** - Content extraction methods compared
- **[LLM Setup Guide](SETUP_STAGE2.md)** - Advanced LLM configuration options

### Development Documentation

See `dev/` subdirectory:

- **[Refactoring Progress](dev/REFACTORING_PROGRESS.md)** - Current code improvement status
- **[Design Patterns](dev/DESIGN_PATTERNS.md)** - Architecture patterns in use
- **[Reorganization Notes](dev/REORGANIZATION.md)** - Project structure history
- **[Future Enhancements](dev/FUTURE_ENHANCEMENTS.md)** - Planned features and improvements

## Features

### Bookmark Management

- Add, edit, delete bookmarks with titles, descriptions, and tags
- 🔍 Multi-tag filtering (AND/OR logic)
- ⭐ Favorites support
- 📊 Multiple sorting options (newest, oldest, alphabetical, favorites-first)
- 🔄 URL validation

### Easy Integration

- 🦊 **Browser Extension** - One-click bookmarking from Firefox/Chrome
- 📱 **iOS Shortcuts** - Share URLs from Safari or any iOS app
- 🌐 **Web Interface** - Direct add and management through the app
- 🎯 **REST API** - Build custom integrations

### LLM-Powered Automation

- 🤖 **Automatic enrichment** - Just send a URL, get title and description automatically
- 🔌 **Multiple providers** - Perplexity, OpenAI, Anthropic (pluggable architecture)
- 📄 **Content extraction** - HTML or Markdown parsing strategies
- 🎯 **Future enhancement** - Automatic tag suggestions based on content

### LLM Service Architecture

The LLM service uses a **composition-based architecture**:

- **Providers**: Pluggable API clients (Perplexity, OpenAI, Anthropic)
- **Extractors**: Content extraction strategies (HTML, Markdown, MCP)
- **Service**: Single orchestrator for all LLM operations

See **[LLM Configuration Guide](LLM_CONFIGURATION.md)** for details.

## API Documentation

### REST Endpoints

**Create Bookmark** - `POST /api/bookmarks`

```json
{
  "url": "https://example.com",
  "tags": ["optional", "tags"],
  "favorite": false
}
```

**Web Routes:**

- `GET /bookmarks` - List bookmarks (supports filtering via query params)
- `GET /bookmarks/<id>` - View bookmark details
- `POST /bookmarks/new` - Create new bookmark
- `POST /bookmarks/<id>/update` - Update existing bookmark
- `POST /bookmarks/delete/<id>` - Delete bookmark
- `POST /bookmarks/<id>/favorite` - Toggle favorite status
- `POST /bookmarks/autofill` - Auto-generate title/description from URL

## Testing

Run the test suite:

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=bookmarks

# Specific test
uv run pytest tests/test_app.py -v
```

## Configuration

Application uses environment variables for configuration. See `CONFIGURATION.md` for details.

**Key environment variables:**

- `BOOKMARKS_DATA_SOURCE` - Path to bookmarks.js file (default: `bookmarks.js`)
- `BOOKMARKS_SECRET_KEY` - Flask secret key (auto-generated if not set)
- `BOOKMARKS_DEBUG` - Enable debug mode (default: `false`)
- `BOOKMARKS_PORT` - Server port (default: `5001`)

See `CONFIGURATION.md` for complete configuration reference.

## Project Structure

```
bookmarks/
├── bookmarks/          # Main application package
│   ├── routes.py       # HTTP routes
│   ├── model.py        # Data access layer
│   ├── repository.py   # Repository pattern
│   ├── services/       # LLM clients, usage tracking
│   └── templates/      # Jinja2 templates
├── tools/              # Utility scripts (see tools/README.md)
├── tests/              # Test suite
├── docs/               # Documentation (you are here)
│   └── dev/            # Development/transitory docs
└── bookmarks.js        # Data storage file
```

## Tools & Utilities

See `../tools/README.md` for documentation on utility scripts:

- `add_bookmarks_from_urls.py` - Bulk import from URL lists
- `check_urls.py` - Async URL validation
- `update_bookmarks.py` - Batch updates
- And more...

## License

This project is licensed under the MIT License.
