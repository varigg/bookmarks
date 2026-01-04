# Technology Stack & Build System

## Core Technologies

### Backend
- **Python 3.12+** - Primary language
- **Flask 3.1+** - Web framework with CORS support
- **Pydantic 2.5+** - Data validation and serialization
- **aiohttp** - Async HTTP client for URL validation
- **JavaScript Data Files** - JSON-based data storage

### Frontend
- **Jinja2 templates** - Server-side rendering
- **CSS** - Custom styling (no framework)
- **Vanilla JavaScript** - Browser extension and web interface

### Development Tools
- **uv** - Python package manager and virtual environment
- **ruff** - Linting and formatting (replaces black, isort, flake8)
- **pytest** - Testing framework with coverage support
- **ty** - Type checking
- **pre-commit** - Git hooks for code quality

## Build System

### Package Management
Uses **uv** for all Python dependency management:
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name

# Development dependencies
uv add --dev package-name
```

### Common Commands

#### Development
```bash
# Run development server
make run
# or
uv run flask run --debug

# Install dependencies
make install
```

#### Code Quality
```bash
# Format, lint, and test (run before commit)
make clean-code

# Individual operations
make format      # Format code with ruff
make lint        # Check code with ruff
make typecheck   # Type check with ty (excludes routes.py)
make test        # Run pytest
make test-coverage  # Run with coverage report
```

#### Docker
```bash
make docker-build   # Build image
make docker-up      # Start with compose
make docker-down    # Stop services
```

## Architecture Patterns

### Service Layer Architecture
- **Repository Pattern** - Data access abstraction (`BookmarkRepository`)
- **Factory Pattern** - LLM provider creation (`LLMFactory`)
- **Composition Pattern** - LLM service orchestration
- **Protocol-based interfaces** - Type-safe abstractions

### Configuration
- **Environment-based config** - All settings via env vars
- **Sensible defaults** - Works out of the box for development
- **No config files required** - Pure environment variable configuration

### Key Environment Variables
```bash
# Data and backup
BOOKMARKS_DATA_SOURCE="bookmarks.js"
BOOKMARKS_BACKUP_ENABLED="true"
BOOKMARKS_BACKUP_COUNT="5"

# LLM configuration
BOOKMARKS_LLM_PROVIDER="perplexity"  # perplexity, openai, anthropic
BOOKMARKS_LLM_CONTENT_FORMAT="html"  # html, markdown

# API keys
PERPLEXITY_API_KEY="your-key"
OPENAI_API_KEY="your-key"
ANTHROPIC_API_KEY="your-key"
```

## Code Style Guidelines

### Python Standards
- **Line length**: 100 characters
- **Target version**: Python 3.12
- **Quote style**: Double quotes
- **Import organization**: isort with known-first-party ["bookmarks"]
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for classes and public methods

### Naming Conventions
- **Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Files/modules**: snake_case
- **Exception**: `dateAdded` field matches JavaScript format for data compatibility

### Testing
- **Framework**: pytest
- **Coverage**: Aim for high coverage, use `--cov=bookmarks`
- **Test files**: `test_*.py` in `tests/` directory
- **Fixtures**: Use `conftest.py` for shared fixtures