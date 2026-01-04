# Requirements Document

## Introduction

This feature creates a static HTML page that can display and interact with bookmarks.js data directly in the browser, following the "mildly dynamic websites" philosophy. The page will work without a server, using only client-side JavaScript to load and filter the bookmarks data, while maintaining the core functionality of the existing Flask application.

## Glossary

- **Static HTML Page**: A standalone HTML file that works without a web server
- **Bookmarks Data**: JSON data stored in bookmarks.js file containing bookmark objects
- **Client-side Filtering**: JavaScript-based filtering that runs in the browser
- **Progressive Enhancement**: Starting with basic HTML functionality and adding JavaScript features
- **Mildly Dynamic**: Minimal JavaScript that enhances static content without complex frameworks

## Requirements

### Requirement 1

**User Story:** As a user, I want to view my bookmarks in a static HTML page, so that I can access them without running a web server.

#### Acceptance Criteria

1. WHEN a user opens the static HTML file in a browser, THE system SHALL load and display all bookmarks from bookmarks.js
2. WHEN the bookmarks.js file is not found or invalid, THE system SHALL display an appropriate error message
3. WHEN bookmarks are displayed, THE system SHALL show title, description, tags, date added, and favorite status for each bookmark
4. WHEN a user clicks on a bookmark, THE system SHALL open the URL in a new tab
5. WHEN the page loads, THE system SHALL display the total count of bookmarks

### Requirement 2

**User Story:** As a user, I want to filter bookmarks by tags, so that I can find specific bookmarks quickly.

#### Acceptance Criteria

1. WHEN the page loads, THE system SHALL display a list of all available tags with their counts
2. WHEN a user clicks on a tag filter, THE system SHALL show only bookmarks containing that tag
3. WHEN multiple tags are selected, THE system SHALL show bookmarks containing ALL selected tags (AND logic)
4. WHEN a tag filter is active, THE system SHALL visually indicate which tags are selected
5. WHEN a user clears tag filters, THE system SHALL show all bookmarks again

### Requirement 3

**User Story:** As a user, I want to sort bookmarks by different criteria, so that I can organize them according to my preferences.

#### Acceptance Criteria

1. WHEN a user selects "newest" sort, THE system SHALL order bookmarks by dateAdded descending
2. WHEN a user selects "oldest" sort, THE system SHALL order bookmarks by dateAdded ascending
3. WHEN a user selects "A-Z" sort, THE system SHALL order bookmarks alphabetically by title
4. WHEN a user selects "Z-A" sort, THE system SHALL order bookmarks reverse alphabetically by title
5. WHEN a user selects "favorites first" sort, THE system SHALL show favorite bookmarks before non-favorites

### Requirement 4

**User Story:** As a user, I want to filter bookmarks by favorites, so that I can quickly access my most important bookmarks.

#### Acceptance Criteria

1. WHEN a user activates the favorites filter, THE system SHALL show only bookmarks marked as favorite
2. WHEN the favorites filter is active, THE system SHALL visually indicate the filter status
3. WHEN a user deactivates the favorites filter, THE system SHALL show all bookmarks again
4. WHEN favorites are displayed, THE system SHALL show a star icon for favorite bookmarks
5. WHEN non-favorites are displayed, THE system SHALL show an empty star icon

### Requirement 5

**User Story:** As a user, I want to search bookmarks by text, so that I can find bookmarks containing specific words.

#### Acceptance Criteria

1. WHEN a user types in the search box, THE system SHALL filter bookmarks containing the search text in title or description
2. WHEN the search is case-insensitive, THE system SHALL match text regardless of capitalization
3. WHEN search text is cleared, THE system SHALL show all bookmarks again
4. WHEN search is combined with other filters, THE system SHALL apply all filters together
5. WHEN no bookmarks match the search, THE system SHALL display a "no results" message

### Requirement 6

**User Story:** As a user, I want the page to work without JavaScript, so that I have basic functionality even if JavaScript is disabled.

#### Acceptance Criteria

1. WHEN JavaScript is disabled, THE system SHALL display all bookmarks in a readable format
2. WHEN JavaScript is disabled, THE system SHALL show bookmark titles as clickable links
3. WHEN JavaScript is disabled, THE system SHALL display tags and metadata for each bookmark
4. WHEN JavaScript is disabled, THE system SHALL provide a fallback message about enhanced features
5. WHEN JavaScript is enabled, THE system SHALL progressively enhance the interface with filtering and sorting

### Requirement 7

**User Story:** As a user, I want the page to be responsive, so that I can use it on different screen sizes.

#### Acceptance Criteria

1. WHEN viewed on mobile devices, THE system SHALL adapt the layout for smaller screens
2. WHEN viewed on desktop, THE system SHALL use a sidebar layout for filters
3. WHEN the screen is narrow, THE system SHALL stack filters vertically
4. WHEN touch interactions are available, THE system SHALL provide appropriate touch targets
5. WHEN the viewport changes, THE system SHALL maintain usability across all screen sizes

### Requirement 8

**User Story:** As a developer, I want the static page to use the same data format as the Flask app, so that both systems can share the same bookmarks.js file.

#### Acceptance Criteria

1. WHEN the static page loads data, THE system SHALL parse the JavaScript variable format from bookmarks.js
2. WHEN bookmark objects are processed, THE system SHALL handle all fields: url, title, description, tags, dateAdded, favorite
3. WHEN date formatting is needed, THE system SHALL display dates in a human-readable format
4. WHEN tags are processed, THE system SHALL handle arrays of string tags
5. WHEN the data structure changes, THE system SHALL gracefully handle missing or additional fields