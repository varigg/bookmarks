# Project Structure & Organization

## Directory Layout

```
bookmarks/                      # Root project directory
├── bookmarks/                  # Main application package
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # Environment-based configuration
│   ├── core/                  # Domain models and exceptions
│   │   ├── domain.py          # Bookmark dataclass and domain models
│   │   └── exceptions.py      # Custom application exceptions
│   ├── data/                  # Data access layer
│   │   ├── datafile.py        # File storage operations (JSON)
│   │   ├── model.py           # Legacy model interface (deprecated)
│   │   └── repository.py      # Repository pattern implementation
│   ├── services/              # Business logic layer
│   │   ├── bookmark_service.py    # Main bookmark operations
│   │   ├── content_extractor.py   # HTML/Markdown extraction
│   │   ├── llm_factory.py         # LLM provider factory
│   │   ├── llm_providers.py       # LLM provider implementations
│   │   ├── llm_service.py         # LLM orchestration service
│   │   └── usage_tracker.py       # LLM usage statistics
│   ├── static/                # Static web assets
│   │   └── styles.css         # Application CSS
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── bookmarks.html     # Main bookmark listing
│   │   ├── bookmark.html      # Single bookmark view
│   │   ├── new_bookmark.html  # Add bookmark form
│   │   ├── 404.html          # Error pages
│   │   └── 500.html
│   └── web/                   # Web layer (Flask routes)
│       ├── filters.py         # Bookmark filtering logic
│       ├── routes.py          # HTTP route handlers
│       ├── sorting.py         # Bookmark sorting utilities
│       ├── utils.py           # Web utility functions
│       └── validation.py      # Pydantic request schemas
├── browser-extension/         # Browser extension code
│   ├── manifest.json         # Extension manifest
│   ├── popup.html/js         # Extension popup interface
│   ├── options.html/js       # Extension settings
│   └── icons/                # Extension icons
├── docs/                     # Documentation
│   ├── README.md            # Main documentation
│   ├── LLM_CONFIGURATION.md # LLM setup guide
│   ├── DEPLOYMENT.md        # Deployment instructions
│   └── dev/                 # Development documentation
├── tests/                   # Test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_app.py         # Application tests
│   └── test_*.py           # Feature-specific tests
├── tools/                  # Utility scripts
│   ├── add_bookmarks_from_urls.py  # Bulk import
│   ├── update_bookmarks.py         # Batch updates
│   └── test_*.py                   # LLM provider tests
├── backup/                 # Automatic backups directory
├── bookmarks.js           # Main data file (JSON)
├── wsgi.py               # WSGI entry point
├── pyproject.toml        # Python project configuration
├── Makefile              # Development automation
└── docker-compose.yml    # Container orchestration
```

## Architecture Layers

### 1. Web Layer (`bookmarks/web/`)
- **Purpose**: HTTP request handling, form validation, response formatting
- **Key files**: `routes.py`, `validation.py`, `filters.py`, `sorting.py`
- **Responsibilities**: Route definitions, request parsing, template rendering
- **Dependencies**: Flask, Pydantic schemas, service layer

### 2. Service Layer (`bookmarks/services/`)
- **Purpose**: Business logic orchestration, external API integration
- **Key files**: `bookmark_service.py`, `llm_service.py`, `llm_factory.py`
- **Responsibilities**: Bookmark operations, LLM integration, content extraction
- **Dependencies**: Data layer, external APIs (LLM providers)

### 3. Data Layer (`bookmarks/data/`)
- **Purpose**: Data persistence and retrieval
- **Key files**: `repository.py`, `datafile.py`
- **Responsibilities**: CRUD operations, file I/O, data validation
- **Dependencies**: Core domain models, file system

### 4. Core Layer (`bookmarks/core/`)
- **Purpose**: Domain models and shared exceptions
- **Key files**: `domain.py`, `exceptions.py`
- **Responsibilities**: Data structures, business rules, error definitions
- **Dependencies**: None (pure domain logic)

## Key Design Patterns

### Repository Pattern
- **Location**: `bookmarks/data/repository.py`
- **Purpose**: Abstracts data access, enables testing with mock data
- **Usage**: `BookmarkRepository` provides CRUD operations

### Factory Pattern
- **Location**: `bookmarks/services/llm_factory.py`
- **Purpose**: Creates LLM providers based on configuration
- **Usage**: `LLMFactory.create_client(provider="perplexity")`

### Service Layer Pattern
- **Location**: `bookmarks/services/bookmark_service.py`
- **Purpose**: Orchestrates business operations across multiple repositories
- **Usage**: Combines repository operations with LLM services

### Composition Pattern
- **Location**: `bookmarks/services/llm_service.py`
- **Purpose**: Combines content extraction with LLM providers
- **Usage**: Configurable content extraction strategies

## File Naming Conventions

### Python Modules
- **snake_case** for all module names
- **Descriptive names** indicating purpose (e.g., `content_extractor.py`)
- **Layer suffix** where appropriate (e.g., `bookmark_service.py`)

### Templates
- **Lowercase with underscores** (e.g., `new_bookmark.html`)
- **Plural for collections** (e.g., `bookmarks.html`)
- **Singular for items** (e.g., `bookmark.html`)

### Static Assets
- **Descriptive names** (e.g., `styles.css`)
- **No versioning in filenames** (handled by Flask)

## Data Flow

### Bookmark Creation
1. **Web Layer**: Route receives POST request, validates with Pydantic
2. **Service Layer**: `BookmarkService` orchestrates operation
3. **LLM Integration**: `LLMService` generates title/description
4. **Data Layer**: `BookmarkRepository` persists to file
5. **Response**: Redirect to bookmark list

### Bookmark Retrieval
1. **Web Layer**: Route processes query parameters
2. **Service Layer**: `BookmarkService` applies filters and sorting
3. **Data Layer**: `BookmarkRepository` loads from file
4. **Response**: Rendered template with bookmark list

## Configuration Management

### Environment Variables
- **Centralized**: All config in `bookmarks/config.py`
- **Typed**: Helper functions with type hints
- **Defaults**: Sensible defaults for development
- **Documentation**: Inline comments explaining each setting

### Data Storage
- **Format**: JSON in `bookmarks.js` file
- **Backup**: Automatic rotation in `backup/` directory
- **Location**: Configurable via `BOOKMARKS_DATA_SOURCE`

## Extension Points

### Adding New LLM Providers
1. Create provider class in `llm_providers.py`
2. Update `LLMFactory.create_client()` method
3. Add configuration variables to `config.py`
4. Update documentation

### Adding New Content Extractors
1. Create extractor class in `content_extractor.py`
2. Update `LLMFactory` to support new format
3. Add configuration option
4. Update validation schemas if needed

### Adding New Routes
1. Add route handler to `routes.py`
2. Create Pydantic schema in `validation.py` if needed
3. Add template in `templates/` directory
4. Update navigation if required