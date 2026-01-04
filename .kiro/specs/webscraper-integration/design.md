# Webscraper Integration Design Document

## Overview

This design integrates a webscraper library (refactored from the existing webscraper tool) directly into the bookmarks application to enable local archiving of bookmarked websites. The integration follows the existing Flask application architecture patterns, using the service layer for business logic and extending the domain model to track archive status.

The solution provides a "Store Locally" feature that downloads complete copies of websites to the local filesystem, making them accessible offline. Users can view archived content through the web interface, with clear indicators showing which bookmarks have been archived.

## Architecture

### High-Level Architecture

The webscraper integration extends the existing three-layer architecture:

```
Web Layer (Flask Routes)
├── Archive routes (/bookmark/<id>/archive, /bookmark/<id>/view-archive)
├── Updated bookmark detail templates
└── Archive status indicators

Service Layer
├── BookmarkService (extended with archive methods)
├── WebscraperService (new - handles archiving operations)
└── ArchiveService (new - manages archive metadata and file operations)

Data Layer
├── BookmarkRepository (extended with archive metadata)
├── ArchiveRepository (new - manages archive file metadata)
└── Filesystem storage for archived content

Domain Layer
├── Bookmark (extended with archive fields)
└── Archive (new domain model)
```

### Integration Points

1. **Webscraper Library Integration**: The existing webscraper tool will be refactored into:
   - A reusable Python library with a clean API
   - A CLI frontend that uses the library (maintaining existing functionality)
   - Direct integration into the bookmarks application

2. **Service Layer Extension**: New services handle archive operations while maintaining separation of concerns

3. **Data Model Extension**: The Bookmark domain model gains archive-related fields without breaking existing functionality

## Components and Interfaces

### Domain Models

#### Extended Bookmark Model
```python
@dataclass
class Bookmark:
    # Existing fields...
    url: str
    title: str
    description: str
    tags: list[str]
    dateAdded: str
    favorite: bool
    
    # New archive fields
    archived: bool = False
    archive_path: str | None = None
    archive_date: str | None = None  # ISO format timestamp
    archive_size: int | None = None  # Size in bytes
```

#### New Archive Model
```python
@dataclass
class Archive:
    bookmark_id: str
    url: str
    archive_path: str
    created_date: str  # ISO format timestamp
    file_size: int
    status: str  # 'completed', 'failed', 'in_progress'
    error_message: str | None = None
```

### Service Layer

#### WebscraperService
```python
class WebscraperService:
    """Service for webscraping operations using the IntelligentWebScraper library."""
    
    def __init__(self, archive_dir: str, delay: float = 1.0, max_retries: int = 3):
        """Initialize with IntelligentWebScraper instance."""
        from webscraper import IntelligentWebScraper
        self.scraper = IntelligentWebScraper(
            output_dir=archive_dir,
            delay=delay,
            max_retries=max_retries
        )
    
    def archive_url(self, url: str) -> ArchiveResult:
        """Archive a URL using the webscraper library."""
        result_path = self.scraper.scrape_article(url)
        # Convert webscraper result to our ArchiveResult format
        
    def get_archive_info(self, archive_path: str) -> ArchiveInfo:
        """Get information about an archived website."""
        
    def validate_archive(self, archive_path: str) -> bool:
        """Validate that an archive is complete and accessible."""
```

#### ArchiveService
```python
class ArchiveService:
    """Service for managing archive metadata and file operations."""
    
    def create_archive(self, bookmark_id: str, url: str) -> Archive:
        """Create a new archive for a bookmark."""
        
    def get_archive_path(self, bookmark_id: str) -> str:
        """Generate the archive path for a bookmark."""
        
    def serve_archived_content(self, archive_path: str, requested_path: str) -> Response:
        """Serve archived content with proper MIME types."""
```

#### Extended BookmarkService
```python
class BookmarkService:
    # Existing methods...
    
    def archive_bookmark(self, bookmark_id: str) -> Archive:
        """Archive a bookmark's content locally."""
        
    def get_archive_status(self, bookmark_id: str) -> dict:
        """Get archive status information for a bookmark."""
        
    def delete_archive(self, bookmark_id: str) -> bool:
        """Delete the local archive for a bookmark."""
```

### Web Layer

#### New Routes
- `POST /bookmark/<id>/archive` - Trigger archiving of a bookmark
- `GET /bookmark/<id>/view-archive` - View archived content
- `GET /bookmark/<id>/view-archive/<path:file_path>` - Serve archived files
- `DELETE /bookmark/<id>/archive` - Delete archived content

#### Archive Filtering Strategy

The main bookmarks page will extend the existing filtering system to include archive status filtering:

**Filter Integration:**
- Extend the existing `FilterState` class in `bookmarks/web/filters.py` to include archive status
- Add archive filter to the existing filter sidebar alongside tags, favorites, and search
- Support three archive filter states: "All" (default), "Archived Only", "Not Archived"

**Filter Implementation:**
```python
class FilterState:
    # Existing fields...
    tags: list[str]
    favorites_only: bool
    search_query: str
    
    # New archive filtering
    archive_filter: str = "all"  # "all", "archived", "not_archived"
```

**UI Filter Controls:**
- Add archive filter dropdown/radio buttons to the filter sidebar
- Show archive status counts: "Archived (15)" / "Not Archived (42)"
- Maintain filter state in URL parameters for bookmarking and sharing
- Clear archive filter when "Clear All Filters" is used

**Filter Logic:**
- Apply archive filtering in `apply_filters()` function alongside existing filters
- Filter based on bookmark's `archived` field value
- Combine with existing AND logic (tags + favorites + search + archive status)
- Maintain performance by filtering in-memory after loading bookmarks

#### Template Updates
- Add "Store Locally" button to bookmark detail pages
- Add "View Local Copy" link for archived bookmarks
- Add archive status indicators to bookmark lists
- Update bookmark detail template to show archive information
- Extend main bookmarks page with archive filtering controls

## Data Models

### Archive Storage Structure
The webscraper library creates this structure automatically:
```
archives/
├── example.com_a1b2c3d4/     # Unique folder per article (webscraper format)
│   ├── article.html          # Clean, readable HTML
│   ├── metadata.txt          # Article information
│   └── images/               # Downloaded images
│       ├── hero_image.jpg
│       └── inline_001.png
└── github.com_x9y8z7w6/      # Another archived site
    ├── article.html
    ├── metadata.txt
    └── images/
```

### Archive Metadata Format
```json
{
  "bookmark_id": "123",
  "url": "https://example.com/page",
  "archive_path": "archives/example.com/bookmark-123",
  "created_date": "2024-12-15T10:30:00Z",
  "file_size": 2048576,
  "status": "completed",
  "files": [
    "index.html",
    "assets/style.css",
    "assets/script.js"
  ]
}
```

### Configuration Extensions
```python
# New configuration options
ARCHIVE_ENABLED: bool = get_config("BOOKMARKS_ARCHIVE_ENABLED", "true")
ARCHIVE_DIR: str = get_config("BOOKMARKS_ARCHIVE_DIR", "archives")
ARCHIVE_TIMEOUT: int = int(get_config("BOOKMARKS_ARCHIVE_TIMEOUT", "30"))
WEBSCRAPER_MAX_RETRIES: int = int(get_config("BOOKMARKS_WEBSCRAPER_MAX_RETRIES", "3"))
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the requirements analysis, the following correctness properties ensure the webscraper integration behaves correctly across all valid inputs and scenarios:

### Property 1: Archive Status Consistency
*For any* bookmark, after successful archiving, the bookmark's archived status should be true and archive metadata should be populated
**Validates: Requirements 1.4**

### Property 2: Webscraper Library Invocation
*For any* valid URL and archive request, the webscraper library should be called with the correct URL and output directory parameters
**Validates: Requirements 1.2, 5.1**

### Property 3: Archive File Verification
*For any* completed archive operation, files should actually exist in the filesystem before the bookmark is marked as archived
**Validates: Requirements 5.3**

### Property 4: Error Handling Consistency
*For any* archiving operation that encounters errors, the system should log detailed information and return user-friendly error messages
**Validates: Requirements 1.5, 5.2, 5.5**

### Property 5: Archive Status Display
*For any* bookmark list or detail view, archived bookmarks should display archive indicators and non-archived bookmarks should not
**Validates: Requirements 3.1, 3.2, 3.3**

### Property 6: Archived Content Serving
*For any* archived bookmark, requesting the local copy should serve the archived content from the correct filesystem location
**Validates: Requirements 2.2**

### Property 7: Archive Directory Organization
*For any* archived content, files should be organized in the expected directory structure based on domain and bookmark ID
**Validates: Requirements 4.2**

### Property 8: Archive Filtering
*For any* bookmark collection, filtering by archive status should return only bookmarks matching the specified archive state
**Validates: Requirements 3.5**

### Property 9: Retry Mechanism
*For any* archiving operation that fails due to network issues, the system should attempt retries according to configuration
**Validates: Requirements 5.4**

### Property 10: Relative Link Handling
*For any* archived content containing relative links, those links should be rewritten to point to the correct local files
**Validates: Requirements 2.4**

### Property 11: Archive Metadata Consistency
*For any* archived bookmark, the archive date and file size metadata should accurately reflect the actual archived content
**Validates: Requirements 3.4**

### Property 12: Filesystem Error Handling
*For any* storage operation that encounters filesystem errors, the system should handle them gracefully and provide appropriate user feedback
**Validates: Requirements 4.5**

## Error Handling

### Archive Operation Errors
- **Network failures**: Implement exponential backoff retry with configurable maximum attempts
- **Filesystem errors**: Catch and log filesystem exceptions, provide user-friendly error messages
- **Webscraper library errors**: Capture library exceptions and translate to application-specific error types
- **Timeout handling**: Respect configured timeout values and gracefully abort long-running operations

### Graceful Degradation
- **Missing webscraper library**: Disable archive features and show informative messages
- **Insufficient disk space**: Detect and report storage issues before attempting archives
- **Permission errors**: Handle filesystem permission issues with clear error messages
- **Corrupted archives**: Detect and handle corrupted or incomplete archive files

### Error Recovery
- **Partial downloads**: Clean up incomplete archives and allow retry
- **Metadata inconsistency**: Validate and repair archive metadata on startup
- **Orphaned files**: Provide utilities to clean up orphaned archive files

## Testing Strategy

### Unit Testing Approach
The testing strategy combines unit tests for specific scenarios with property-based tests for comprehensive coverage:

**Unit Tests Focus Areas:**
- Configuration loading and validation
- Error message formatting and user feedback
- Template rendering with archive status indicators
- Route handler behavior for archive operations
- Integration points with the webscraper library

**Key Unit Test Categories:**
- Archive service initialization and configuration
- Bookmark model extensions and serialization
- Route handlers for archive operations (POST /archive, GET /view-archive)
- Error handling for specific failure scenarios
- Template rendering with archive status data

### Property-Based Testing Approach
Property-based testing will use **Hypothesis** as the testing library, configured to run a minimum of 100 iterations per property test.

**Property Test Requirements:**
- Each property-based test must be tagged with a comment referencing the design document property
- Tag format: `**Feature: webscraper-integration, Property {number}: {property_text}**`
- Each correctness property must be implemented by a single property-based test
- Tests should generate realistic bookmark data, URLs, and archive scenarios

**Property Test Coverage:**
- Archive status consistency across bookmark operations
- Webscraper library parameter validation with generated URLs
- File system operations with various directory structures
- Error handling with simulated failure conditions
- Archive metadata accuracy with generated content
- Filtering operations with mixed archive states

**Generator Strategies:**
- Valid and invalid URL generation for archive testing
- Bookmark data with various archive states
- Filesystem path generation for directory structure testing
- Error condition simulation for failure testing
- Archive metadata generation for consistency testing

The dual testing approach ensures both concrete functionality (unit tests) and general correctness (property tests) are validated, providing comprehensive coverage of the webscraper integration feature.