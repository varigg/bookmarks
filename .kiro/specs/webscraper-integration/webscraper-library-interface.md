# Webscraper Library Interface Specification

## Overview

This document defines the interface specification for a Python webscraper library that will be integrated into the bookmarks application. The library should be refactored from the existing webscraper tool at `/home/varigg/projects/python/webscraper` to provide a clean, reusable API for downloading and archiving websites.

## Package Structure

The webscraper should be packaged as a proper Python library with the following structure:

```
webscraper/
├── pyproject.toml          # Package configuration
├── README.md              # Library documentation
├── webscraper/            # Main package
│   ├── __init__.py       # Package exports
│   ├── client.py         # Main WebscraperClient class
│   ├── models.py         # Data models and types
│   ├── exceptions.py     # Custom exceptions
│   └── utils.py          # Utility functions
├── cli/                  # Command-line interface (optional)
│   ├── __init__.py
│   └── main.py          # CLI frontend using the library
└── tests/               # Test suite
    ├── __init__.py
    └── test_client.py
```

## Core Interface

### Main Client Class

```python
from webscraper import WebscraperClient, ArchiveResult, ArchiveConfig

class WebscraperClient:
    """Main client for webscraping operations."""
    
    def __init__(self, config: ArchiveConfig | None = None):
        """
        Initialize the webscraper client.
        
        Args:
            config: Optional configuration object. Uses defaults if None.
        """
        pass
    
    def archive_url(self, url: str, output_dir: str) -> ArchiveResult:
        """
        Archive a URL to the specified directory.
        
        Args:
            url: The URL to archive
            output_dir: Directory where archived content should be stored
            
        Returns:
            ArchiveResult object with operation details
            
        Raises:
            WebscraperError: Base exception for webscraper errors
            NetworkError: Network-related errors (timeouts, DNS, etc.)
            FileSystemError: File I/O related errors
            ValidationError: Invalid input parameters
        """
        pass
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is accessible and scrapeable.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        pass
    
    def get_archive_info(self, archive_path: str) -> ArchiveInfo:
        """
        Get information about an existing archive.
        
        Args:
            archive_path: Path to the archived content directory
            
        Returns:
            ArchiveInfo object with metadata about the archive
            
        Raises:
            FileNotFoundError: If archive path doesn't exist
            CorruptedArchiveError: If archive is incomplete or corrupted
        """
        pass
```

## Data Models

### ArchiveConfig

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ArchiveConfig:
    """Configuration for webscraping operations."""
    
    # Timeout settings
    timeout: int = 30  # Total timeout in seconds
    connect_timeout: int = 10  # Connection timeout in seconds
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0  # Delay between retries in seconds
    
    # Content settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB max file size
    follow_redirects: bool = True
    max_redirects: int = 10
    
    # User agent and headers
    user_agent: str = "WebscraperLibrary/1.0"
    custom_headers: Optional[dict[str, str]] = None
    
    # Content filtering
    allowed_domains: Optional[list[str]] = None  # Restrict to specific domains
    blocked_extensions: list[str] = None  # File extensions to skip
    
    # Archive organization
    preserve_structure: bool = True  # Keep original directory structure
    create_index: bool = True  # Create index.html if not present
```

### ArchiveResult

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class ArchiveStatus(Enum):
    """Status of archive operation."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"  # Some files failed but main content succeeded
    FAILED = "failed"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    FILESYSTEM_ERROR = "filesystem_error"

@dataclass
class ArchiveResult:
    """Result of an archive operation."""
    
    # Operation status
    status: ArchiveStatus
    success: bool  # Convenience property: status == SUCCESS
    
    # Input parameters
    url: str
    output_dir: str
    
    # Results
    archive_path: str  # Full path to archived content
    main_file: str  # Path to main HTML file (usually index.html)
    
    # Metadata
    start_time: datetime
    end_time: datetime
    duration: float  # Duration in seconds
    
    # Content information
    files_downloaded: int
    total_size: int  # Total size in bytes
    content_type: str  # MIME type of main content
    
    # Error information (if applicable)
    error_message: Optional[str] = None
    failed_urls: list[str] = None  # URLs that failed to download
    
    # Additional metadata
    title: Optional[str] = None  # Extracted page title
    description: Optional[str] = None  # Meta description if available
```

### ArchiveInfo

```python
@dataclass
class ArchiveInfo:
    """Information about an existing archive."""
    
    # Basic info
    archive_path: str
    main_file: str
    created_date: datetime
    
    # Content info
    total_files: int
    total_size: int
    
    # Metadata
    original_url: str
    title: Optional[str] = None
    
    # Validation
    is_complete: bool  # Whether archive appears complete
    is_accessible: bool  # Whether main file is readable
    
    # File listing
    files: list[str] = None  # List of all files in archive
```

## Exception Hierarchy

```python
class WebscraperError(Exception):
    """Base exception for all webscraper errors."""
    pass

class NetworkError(WebscraperError):
    """Network-related errors (timeouts, DNS failures, HTTP errors)."""
    
    def __init__(self, message: str, url: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code

class FileSystemError(WebscraperError):
    """File system related errors (permissions, disk space, I/O)."""
    
    def __init__(self, message: str, path: str):
        super().__init__(message)
        self.path = path

class ValidationError(WebscraperError):
    """Invalid input parameters or configuration."""
    pass

class CorruptedArchiveError(WebscraperError):
    """Archive exists but is incomplete or corrupted."""
    
    def __init__(self, message: str, archive_path: str):
        super().__init__(message)
        self.archive_path = archive_path

class TimeoutError(NetworkError):
    """Operation timed out."""
    
    def __init__(self, message: str, url: str, timeout: int):
        super().__init__(message, url)
        self.timeout = timeout
```

## Package Exports

The main `__init__.py` should export the primary interface:

```python
# webscraper/__init__.py
from .client import WebscraperClient
from .models import ArchiveConfig, ArchiveResult, ArchiveInfo, ArchiveStatus
from .exceptions import (
    WebscraperError,
    NetworkError,
    FileSystemError,
    ValidationError,
    CorruptedArchiveError,
    TimeoutError,
)

__version__ = "1.0.0"
__all__ = [
    "WebscraperClient",
    "ArchiveConfig",
    "ArchiveResult", 
    "ArchiveInfo",
    "ArchiveStatus",
    "WebscraperError",
    "NetworkError",
    "FileSystemError",
    "ValidationError",
    "CorruptedArchiveError",
    "TimeoutError",
]
```

## Usage Examples

### Basic Usage

```python
from webscraper import WebscraperClient

# Simple usage with defaults
client = WebscraperClient()
result = client.archive_url("https://example.com", "/path/to/archives/example.com")

if result.success:
    print(f"Archived {result.files_downloaded} files to {result.archive_path}")
    print(f"Main file: {result.main_file}")
else:
    print(f"Archive failed: {result.error_message}")
```

### Advanced Configuration

```python
from webscraper import WebscraperClient, ArchiveConfig

# Custom configuration
config = ArchiveConfig(
    timeout=60,
    max_retries=5,
    user_agent="BookmarksApp/1.0",
    blocked_extensions=[".exe", ".zip", ".tar.gz"],
    max_file_size=50 * 1024 * 1024  # 50MB limit
)

client = WebscraperClient(config)
result = client.archive_url("https://example.com", "/archives/example")
```

### Error Handling

```python
from webscraper import WebscraperClient, NetworkError, FileSystemError

client = WebscraperClient()

try:
    result = client.archive_url("https://example.com", "/archives/example")
except NetworkError as e:
    print(f"Network error for {e.url}: {e}")
    if e.status_code:
        print(f"HTTP Status: {e.status_code}")
except FileSystemError as e:
    print(f"File system error at {e.path}: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Archive Directory Structure

The library should create archives with this structure:

```
output_dir/
├── index.html          # Main HTML file (or original filename)
├── assets/            # CSS, JS, images, etc.
│   ├── css/
│   ├── js/
│   └── images/
├── pages/             # Additional HTML pages (if any)
└── metadata.json      # Archive metadata
```

### Metadata Format

```json
{
  "url": "https://example.com",
  "title": "Example Website",
  "description": "Example website description",
  "archived_date": "2024-12-15T10:30:00Z",
  "files_count": 15,
  "total_size": 2048576,
  "main_file": "index.html",
  "webscraper_version": "1.0.0"
}
```

## Installation Requirements

The library should be installable via pip/uv:

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "webscraper"
version = "1.0.0"
description = "Website archiving library"
dependencies = [
    "requests>=2.28.0",
    "beautifulsoup4>=4.11.0",
    "lxml>=4.9.0",
    "urllib3>=1.26.0",
]

[project.optional-dependencies]
cli = ["click>=8.0.0"]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]
```

## Integration Points

The bookmarks application will use the library like this:

```python
# In bookmarks/services/webscraper_service.py
from webscraper import WebscraperClient, ArchiveConfig, NetworkError

class WebscraperService:
    def __init__(self):
        config = ArchiveConfig(
            timeout=30,
            max_retries=3,
            user_agent="BookmarksApp/1.0"
        )
        self.client = WebscraperClient(config)
    
    def archive_bookmark(self, url: str, output_dir: str) -> dict:
        try:
            result = self.client.archive_url(url, output_dir)
            return {
                "success": result.success,
                "archive_path": result.archive_path,
                "file_count": result.files_downloaded,
                "size": result.total_size,
                "error": result.error_message
            }
        except NetworkError as e:
            return {"success": False, "error": f"Network error: {e}"}
```

## Testing Requirements

The library should include comprehensive tests covering:

- Successful archiving of various website types
- Error handling for network failures, timeouts, filesystem errors
- Configuration validation
- Archive validation and metadata extraction
- Edge cases (redirects, large files, special characters)

## CLI Interface (Optional)

If maintaining CLI compatibility, create a separate CLI package that uses the library:

```python
# cli/main.py
import click
from webscraper import WebscraperClient, ArchiveConfig

@click.command()
@click.argument('url')
@click.argument('output_dir')
@click.option('--timeout', default=30, help='Timeout in seconds')
def archive(url, output_dir, timeout):
    """Archive a website to a local directory."""
    config = ArchiveConfig(timeout=timeout)
    client = WebscraperClient(config)
    
    result = client.archive_url(url, output_dir)
    
    if result.success:
        click.echo(f"Successfully archived {url} to {result.archive_path}")
    else:
        click.echo(f"Failed to archive {url}: {result.error_message}")
        exit(1)
```

This specification provides a complete interface contract that another agent can implement while ensuring seamless integration with the bookmarks application.