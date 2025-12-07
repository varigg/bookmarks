# Bookmark Management Application - Documentation

This is a Flask-based web application for managing bookmarks with LLM-powered features.

## Quick Links

### Getting Started

- **[Main Project README](../README.md)** - Installation and quick start
- **[Adding Bookmarks](ADDING_BOOKMARKS.md)** - How to add bookmarks manually or in bulk
- **[LLM Quickstart](QUICKSTART_LLM.md)** - Enable auto-generation of titles/descriptions

### User Guides

- **[MCP Integration Guide](MCP_GUIDE.md)** - Model Context Protocol setup and usage
- **[MarkItDown Comparison](MARKITDOWN_COMPARISON.md)** - Content extraction methods compared
- **[Stage 2 Setup](SETUP_STAGE2.md)** - Advanced LLM configuration options

### Development Documentation

See `dev/` subdirectory:

- **[Refactoring Progress](dev/REFACTORING_PROGRESS.md)** - Current code improvement status
- **[Design Patterns](dev/DESIGN_PATTERNS.md)** - Architecture patterns in use
- **[Reorganization Notes](dev/REORGANIZATION.md)** - Project structure history
- **[Future Enhancements](dev/FUTURE_ENHANCEMENTS.md)** - Planned features and improvements

## Features

- Add, edit, delete bookmarks with titles, descriptions, and tags
- 🤖 LLM-powered auto-generation (Perplexity API)
- 🔍 Multi-tag filtering (AND/OR logic)
- ⭐ Favorites support
- 📊 Multiple sorting options (newest, oldest, alphabetical, favorites-first)
- 🌐 REST API for external integration
- 🔄 Async URL checking

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

Application uses Dynaconf for configuration management via `settings.toml`:

```toml
[default]
DEBUG = true
SECRET_KEY = "your-secret-key"
DATA_SOURCE = "bookmarks.js"

[default.env_vars]
PERPLEXITY_API_KEY = "pplx-xxx"
```

Environment-specific settings:

- Create `settings.dev.toml` or `settings.prod.toml`
- Set `ENV_FOR_DYNACONF=dev` environment variable

See [Dynaconf documentation](https://www.dynaconf.com/) for details.

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
