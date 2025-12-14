# Bookmark Management Application

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A self-hosted Flask web application for managing bookmarks with LLM-powered auto-generation of titles and descriptions.

## Overview

This application is designed to run on your desktop or home server, providing a central hub for managing your bookmarks with automatic enrichment via LLMs.

### Intended Workflow

1. **Run the app** on your desktop or home network server
2. **Add bookmarks seamlessly** using:
   - 🦊 **Browser extension** (Firefox/Chrome) - One-click bookmarking from any webpage
   - 📱 **iOS Shortcuts** - Share URLs directly from Safari or any iOS app
   - 🌐 **Web interface** - Use the "Add" button directly in the app
3. **Automatic enrichment** - The app automatically generates titles and descriptions using LLMs
4. **Optional tagging** - Future enhancement to auto-suggest tags based on content

The key advantage: You don't need to manually write descriptions. Just send URLs to your app, and it handles the rest.

## Quick Start

### Local Development (One-Command)

```bash
# Clone and setup (copy-paste ready)
git clone https://github.com/varigg/bookmarks.git && cd bookmarks && uv sync && cp .env.example .env && echo "Setup complete! Edit .env with your API keys, then run: uv run flask --app wsgi run --debug"
```

### Docker (One-Command)

```bash
# Clone and run with Docker (copy-paste ready)
git clone https://github.com/varigg/bookmarks.git && cd bookmarks && cp .env.example .env && echo "Edit .env with your API keys, then run: docker compose up --build -d"
```

### Step-by-Step Setup

**Local Development:**
```bash
# 1. Clone the repository
git clone https://github.com/varigg/bookmarks.git
cd bookmarks

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and add your LLM API keys

# 4. Run the application
uv run flask --app wsgi run --debug
```

**Docker:**
```bash
# 1. Clone the repository
git clone https://github.com/varigg/bookmarks.git
cd bookmarks

# 2. Configure environment
cp .env.example .env
# Edit .env and add your LLM API keys

# 3. Build and run with Docker Compose
docker compose up --build -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

Visit `http://localhost:5000` to access the application.

## Documentation

All documentation has been organized in the `docs/` directory:

### User Documentation

- **[Browser Extension](docs/browser-extension/README.md)** - One-click bookmarking from Firefox/Chrome
- **[iOS Shortcuts](docs/IOS_SHORTCUTS.md)** - Share URLs from Safari and iOS apps
- **[Main Documentation](docs/README.md)** - Complete application documentation
- **[LLM Configuration Guide](docs/LLM_CONFIGURATION.md)** - Complete guide to LLM service configuration
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Running on your home server
- **[Adding Bookmarks](docs/ADDING_BOOKMARKS.md)** - Guide to adding bookmarks (including bulk import)
- **[LLM Quickstart](docs/QUICKSTART_LLM.md)** - Quick start for LLM features
- **[MCP Integration Guide](docs/MCP_GUIDE.md)** - Model Context Protocol setup

### Development Documentation

- **[Refactoring Progress](docs/dev/REFACTORING_PROGRESS.md)** - Current refactoring status
- **[Reorganization Notes](docs/dev/REORGANIZATION.md)** - Project structure changes
- **[Design Patterns](docs/dev/DESIGN_PATTERNS.md)** - Architecture patterns used
- **[Future Enhancements](docs/dev/FUTURE_ENHANCEMENTS.md)** - Planned features

## Features

### Core Functionality

- 📚 Bookmark management with tags and descriptions
- 🔍 Multi-tag filtering with AND/OR logic
- ⭐ Favorites support
- 📊 Multiple sorting options (newest, oldest, alphabetical, favorites-first)
- 🔄 Async URL validation

### Integration Options

- 🦊 **Browser Extension** - One-click bookmarking from Firefox/Chrome
- 📱 **iOS Shortcuts** - Share from Safari or any iOS app
- 🌐 **Web Interface** - Add and manage bookmarks directly
- 🎯 **REST API** - For custom integrations

### LLM-Powered Enrichment

- 🤖 **Automatic title and description generation** - Just send URLs, the app does the rest
- 🔌 **Multiple LLM providers** - Perplexity, OpenAI, Anthropic
- 📄 **Flexible content extraction** - HTML or Markdown parsing
- 🎯 **Future: Auto-tagging** - Planned enhancement for automatic tag suggestions

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
