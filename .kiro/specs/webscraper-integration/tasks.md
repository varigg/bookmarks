# Implementation Plan

- [ ] 1. Set up webscraper library integration and core interfaces
  - Install webscraper library as editable dependency: `uv add -e ../webscraper`
  - Test webscraper library import: `from webscraper import IntelligentWebScraper`
  - Verify basic functionality with a test URL using the IntelligentWebScraper class
  - Set up basic configuration for archive directory and timeout settings
  - _Requirements: 4.1, 4.4_

- [ ] 2. Extend domain models for archive support
  - [ ] 2.1 Add archive fields to Bookmark domain model
    - Add archived, archive_path, archive_date, archive_size fields to Bookmark dataclass
    - Update Bookmark.from_dict() and to_dict() methods to handle new fields
    - Ensure backward compatibility with existing bookmark data
    - _Requirements: 6.2_

  - [ ]* 2.2 Write property test for bookmark archive fields
    - **Property 1: Archive Status Consistency**
    - **Validates: Requirements 1.4**

  - [ ] 2.3 Create Archive domain model
    - Implement Archive dataclass with bookmark_id, url, archive_path, created_date, file_size, status fields
    - Add factory methods for creating new archives
    - _Requirements: 6.2_

  - [ ]* 2.4 Write property test for archive metadata consistency
    - **Property 11: Archive Metadata Consistency**
    - **Validates: Requirements 3.4**

- [ ] 3. Implement archive services layer
  - [ ] 3.1 Create WebscraperService for library integration
    - Create `bookmarks/services/webscraper_service.py` following existing service patterns
    - Implement WebscraperService class that wraps IntelligentWebScraper from the webscraper library
    - Use IntelligentWebScraper.scrape_article() method for archiving URLs
    - Add error handling and logging consistent with existing services (bookmark_service.py, llm_service.py)
    - Configure webscraper with appropriate delay, output_dir, and retry settings
    - _Requirements: 1.2, 5.1, 5.2_

  - [ ]* 3.2 Write property test for webscraper library invocation
    - **Property 2: Webscraper Library Invocation**
    - **Validates: Requirements 1.2, 5.1**

  - [ ] 3.3 Create ArchiveService for file management
    - Create `bookmarks/services/archive_service.py` following existing service layer patterns
    - Implement ArchiveService with methods for path generation and content serving
    - Add directory structure organization (domain-based paths) in configured archive directory
    - Implement file verification and metadata extraction consistent with existing data patterns
    - _Requirements: 4.2, 5.3_

  - [ ]* 3.4 Write property test for archive directory organization
    - **Property 7: Archive Directory Organization**
    - **Validates: Requirements 4.2**

  - [ ]* 3.5 Write property test for archive file verification
    - **Property 3: Archive File Verification**
    - **Validates: Requirements 5.3**

- [ ] 4. Extend BookmarkService with archive operations
  - [ ] 4.1 Add archive methods to BookmarkService
    - Extend existing `bookmarks/services/bookmark_service.py` with archive methods
    - Implement archive_bookmark() method that coordinates WebscraperService and ArchiveService
    - Add get_archive_status() method for retrieving archive information
    - Integrate error handling and user feedback following existing patterns
    - _Requirements: 1.4, 1.5_

  - [ ]* 4.2 Write property test for error handling consistency
    - **Property 4: Error Handling Consistency**
    - **Validates: Requirements 1.5, 5.2, 5.5**

  - [ ]* 4.3 Write property test for retry mechanism
    - **Property 9: Retry Mechanism**
    - **Validates: Requirements 5.4**

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement web layer archive routes
  - [ ] 6.1 Add archive routes to Flask application
    - Extend existing `bookmarks/web/routes.py` with archive routes following existing patterns
    - Create POST /bookmark/<id>/archive route for triggering archives
    - Create GET /bookmark/<id>/view-archive routes for serving archived content
    - Add proper error handling and status responses consistent with existing routes
    - _Requirements: 1.1, 2.2_

  - [ ]* 6.2 Write property test for archived content serving
    - **Property 6: Archived Content Serving**
    - **Validates: Requirements 2.2**

  - [ ] 6.3 Implement relative link handling in archived content
    - Add link rewriting functionality for relative URLs in archived content
    - Ensure archived content maintains proper internal navigation
    - _Requirements: 2.4_

  - [ ]* 6.4 Write property test for relative link handling
    - **Property 10: Relative Link Handling**
    - **Validates: Requirements 2.4**

- [ ] 7. Extend filtering system for archive status
  - [ ] 7.1 Update FilterState class for archive filtering
    - Extend existing `bookmarks/web/filters.py` FilterState class with archive_filter field
    - Update from_request_args() method to parse archive filter parameters
    - Extend to_dict() method to include archive filter state
    - _Requirements: 3.5_

  - [ ] 7.2 Implement archive filtering logic
    - Update apply_filters() function to handle archive status filtering
    - Add support for "all", "archived", "not_archived" filter states
    - Ensure filtering works with existing tag, favorite, and search filters
    - _Requirements: 3.5_

  - [ ]* 7.3 Write property test for archive filtering
    - **Property 8: Archive Filtering**
    - **Validates: Requirements 3.5**

- [ ] 8. Update templates and UI for archive features
  - [ ] 8.1 Add archive controls to bookmark detail pages
    - Add "Store Locally" button to bookmark detail template
    - Add "View Local Copy" link for archived bookmarks
    - Include archive status and metadata display
    - _Requirements: 1.1, 2.1, 3.4_

  - [ ] 8.2 Update bookmark list templates with archive indicators
    - Add archive status indicators to bookmark list items
    - Show archive icons/badges for archived bookmarks
    - Display archive dates and file sizes where appropriate
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 8.3 Write property test for archive status display
    - **Property 5: Archive Status Display**
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [ ] 8.4 Add archive filter controls to main bookmarks page
    - Extend filter sidebar with archive status dropdown/radio buttons
    - Add archive status counts to filter options
    - Ensure filter state persistence in URLs
    - _Requirements: 3.5_

- [ ] 9. Implement error handling and graceful degradation
  - [ ] 9.1 Add graceful handling for missing webscraper library
    - Detect webscraper library availability on startup
    - Disable archive features when library is not available
    - Show appropriate user messages for disabled features
    - _Requirements: 4.3_

  - [ ] 9.2 Implement filesystem error handling
    - Add comprehensive error handling for disk space, permissions, and I/O errors
    - Provide user-friendly error messages for storage issues
    - Implement cleanup for failed archive operations
    - _Requirements: 4.5_

  - [ ]* 9.3 Write property test for filesystem error handling
    - **Property 12: Filesystem Error Handling**
    - **Validates: Requirements 4.5**

- [ ] 10. Add configuration and environment setup
  - [ ] 10.1 Extend configuration module for archive settings
    - Add ARCHIVE_ENABLED, ARCHIVE_DIR, ARCHIVE_TIMEOUT configuration options
    - Update config.py with archive-related environment variable handling
    - Add configuration validation and default values
    - _Requirements: 4.1, 4.4_

  - [ ] 10.2 Create archive directory initialization
    - Add startup logic to create archive directories if they don't exist
    - Implement directory structure setup (domain-based organization)
    - Add permissions and accessibility checks
    - _Requirements: 4.2_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.