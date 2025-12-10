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
- **[LLM Configuration Guide](docs/LLM_CONFIGURATION.md)** - Complete guide to LLM service configuration
- **[LLM Quickstart](docs/QUICKSTART_LLM.md)** - Quick start for LLM features
- **[MCP Integration Guide](docs/MCP_GUIDE.md)** - Model Context Protocol setup
- **[MarkItDown Comparison](docs/MARKITDOWN_COMPARISON.md)** - Content extraction comparison
- **[LLM Setup Guide](docs/SETUP_STAGE2.md)** - Advanced LLM configuration

### Development Documentation

- **[Refactoring Progress](docs/dev/REFACTORING_PROGRESS.md)** - Current refactoring status
- **[Reorganization Notes](docs/dev/REORGANIZATION.md)** - Project structure changes
- **[Design Patterns](docs/dev/DESIGN_PATTERNS.md)** - Architecture patterns used
- **[Future Enhancements](docs/dev/FUTURE_ENHANCEMENTS.md)** - Planned features

## Features

- 📚 Bookmark management with tags and descriptions
- 🤖 **Flexible LLM integration** - Multiple providers (Perplexity, OpenAI, Anthropic) with pluggable content extraction (HTML, Markdown)
- 🔍 Multi-tag filtering with AND/OR logic
- ⭐ Favorites support
- 🔄 Async URL checking
- 📊 Multiple sorting options (newest, oldest, alphabetical, favorites-first)
- 🎯 REST API for external integration

## LLM Service Architecture

The application uses a **composition-based architecture** for maximum flexibility:

- **LLM Providers** - Pluggable API clients (Perplexity, OpenAI, Anthropic)
- **Content Extractors** - Multiple strategies (HTML, Markdown, MCP)
- **Single Orchestrator** - LLMService handles all common logic (retry, prompts, parsing)

**See [LLM Configuration Guide](docs/LLM_CONFIGURATION.md) for complete details on configuration options.**

## Project Structure

```
bookmarks/
├── bookmarks/          # Main application package
│   ├── __init__.py
│   ├── routes.py       # HTTP routes
│   ├── model.py        # Data access wrapper
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

Configuration is managed via environment variables for easy self-hosting. See **[CONFIGURATION.md](CONFIGURATION.md)** for detailed options.

### Quick Configuration

| Variable                       | Default        | Description                                               |
| ------------------------------ | -------------- | --------------------------------------------------------- |
| `BOOKMARKS_DATA_SOURCE`        | `bookmarks.js` | Path to the bookmarks data file                           |
| `BOOKMARKS_BACKUP_ENABLED`     | `true`         | Enable automatic backups on startup                       |
| `BOOKMARKS_BACKUP_COUNT`       | `5`            | Number of backups to keep                                 |
| `BOOKMARKS_LLM_PROVIDER`       | `perplexity`   | LLM provider (perplexity/perplexity-mcp/openai/anthropic) |
| `BOOKMARKS_LLM_CONTENT_FORMAT` | `html`         | Content extraction (html/markdown)                        |

### Environment Variables for LLM Features

```bash
# API Keys
export PERPLEXITY_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"      # When using OpenAI
export ANTHROPIC_API_KEY="your-anthropic-key" # When using Anthropic

# Optional: Configure provider and content format
export BOOKMARKS_LLM_PROVIDER="perplexity"          # Default: perplexity, perplexity-mcp, openai, anthropic
export BOOKMARKS_LLM_CONTENT_FORMAT="html"          # Default: html or markdown

# Example: Use Perplexity MCP instead of direct API
export BOOKMARKS_LLM_PROVIDER="perplexity-mcp"
```

**See [LLM Configuration Guide](docs/LLM_CONFIGURATION.md) for complete configuration options.**

No configuration file needed! Just set environment variables and run the application.

Note: example commands and docs sometimes show port `5001`; the actual port used by the server is controlled by the `BOOKMARKS_PORT` environment variable (or other runtime overrides). If you run the server on port `5000`, use that port in URLs instead.

## License

This project is licensed under the MIT License.
