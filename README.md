# Bookmark Management Application

A Flask-based web application for managing bookmarks with LLM-powered auto-generation of titles and descriptions.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the application
uv run flask --app wsgi run --debug
```

Visit `http://localhost:5000` to access the application.

## Documentation

All documentation has been organized in the `docs/` directory:

### User Documentation

- **[Main Documentation](docs/README.md)** - Complete application documentation
- **[Adding Bookmarks](docs/ADDING_BOOKMARKS.md)** - Guide to adding bookmarks
- **[LLM Quickstart](docs/QUICKSTART_LLM.md)** - Using LLM features for auto-generation
- **[MCP Integration Guide](docs/MCP_GUIDE.md)** - Model Context Protocol setup
- **[MarkItDown Comparison](docs/MARKITDOWN_COMPARISON.md)** - Content extraction comparison
- **[Stage 2 Setup](docs/SETUP_STAGE2.md)** - Advanced LLM setup

### Development Documentation

- **[Refactoring Progress](docs/dev/REFACTORING_PROGRESS.md)** - Current refactoring status
- **[Reorganization Notes](docs/dev/REORGANIZATION.md)** - Project structure changes
- **[Design Patterns](docs/dev/DESIGN_PATTERNS.md)** - Architecture patterns used
- **[Future Enhancements](docs/dev/FUTURE_ENHANCEMENTS.md)** - Planned features

## Features

- 📚 Bookmark management with tags and descriptions
- 🤖 LLM-powered auto-generation of titles and descriptions (Perplexity)
- 🔍 Multi-tag filtering with AND/OR logic
- ⭐ Favorites support
- 🔄 Async URL checking
- 📊 Multiple sorting options (newest, oldest, alphabetical, favorites-first)
- 🎯 REST API for external integration

## Project Structure

```
bookmarks/
├── bookmarks/          # Main application package
│   ├── __init__.py
│   ├── routes.py       # HTTP routes
│   ├── model.py        # Data access (compatibility layer)
│   ├── repository.py   # Repository pattern for data access
│   ├── datafile.py     # File storage operations
│   ├── exceptions.py   # Custom exceptions
│   ├── services/       # Service layer (LLM clients, etc.)
│   └── templates/      # Jinja2 templates
├── tools/              # Utility scripts
├── tests/              # Test suite
├── docs/               # Documentation
│   └── dev/            # Development/transitory docs
└── bookmarks.js        # Data file
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=bookmarks

# Run specific test file
uv run pytest tests/test_app.py -v
```

## Configuration

Configuration is managed via `settings.toml` using Dynaconf:

```toml
[default]
DEBUG = true
SECRET_KEY = "your-secret-key"
DATA_SOURCE = "bookmarks.js"

[default.env_vars]
PERPLEXITY_API_KEY = "your-api-key"
```

## License

This project is licensed under the MIT License.
