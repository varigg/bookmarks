# Static Bookmarks Viewer Design Document

## Overview

The Static Bookmarks Viewer is a standalone HTML page that provides bookmark management functionality without requiring a web server. Following the "mildly dynamic websites" philosophy, it starts with semantic HTML that works without JavaScript and progressively enhances the experience with minimal client-side scripting.

The design emphasizes:
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Minimal Dependencies**: No external frameworks or libraries
- **Data Compatibility**: Uses the same bookmarks.js format as the Flask application
- **Responsive Design**: Works across all device sizes
- **Performance**: Fast loading and smooth interactions

## Architecture

### Core Principles

1. **HTML First**: The page structure is meaningful and functional without JavaScript
2. **CSS for Layout**: Responsive design handled entirely through CSS
3. **JavaScript for Enhancement**: Filtering, sorting, and search added as enhancements
4. **No Build Process**: Single HTML file with embedded CSS and JavaScript
5. **Data Separation**: Bookmarks data remains in separate bookmarks.js file

### File Structure

```
static-bookmarks.html          # Main HTML file
bookmarks.js                   # Data file (shared with Flask app)
```

### Loading Strategy

The page uses a script tag to load bookmarks.js, which defines a global `bookmarks` variable. This approach:
- Works with existing data format
- Requires no CORS configuration
- Enables offline usage
- Maintains compatibility with Flask app

## Components and Interfaces

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Meta tags, title, embedded CSS -->
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <!-- Filters and controls -->
        </aside>
        <main class="content">
            <!-- Bookmark list -->
        </main>
    </div>
    <!-- Embedded JavaScript -->
    <script src="bookmarks.js"></script>
    <script>
        // Enhancement JavaScript
    </script>
</body>
</html>
```

### CSS Architecture

- **Mobile-first responsive design**
- **CSS Grid for main layout**
- **Flexbox for component layouts**
- **CSS custom properties for theming**
- **No external dependencies**

### JavaScript Modules

#### 1. Data Loader
```javascript
class BookmarkLoader {
    static loadBookmarks() // Loads and validates bookmarks data
    static handleLoadError() // Shows error message for missing/invalid data
}
```

#### 2. Filter Engine
```javascript
class FilterEngine {
    constructor(bookmarks)
    filterByTags(tags) // AND logic for multiple tags
    filterByFavorites(favoritesOnly)
    filterBySearch(searchText) // Case-insensitive title/description search
    combineFilters(filters) // Applies multiple filters together
}
```

#### 3. Sort Engine
```javascript
class SortEngine {
    static sortByNewest(bookmarks)
    static sortByOldest(bookmarks)
    static sortAlphabetical(bookmarks)
    static sortReverseAlphabetical(bookmarks)
    static sortFavoritesFirst(bookmarks)
}
```

#### 4. UI Controller
```javascript
class UIController {
    constructor()
    renderBookmarks(bookmarks) // Updates bookmark display
    renderTagFilters(tags) // Updates tag filter UI
    updateCounts(count) // Updates bookmark count display
    showNoResults() // Shows empty state
}
```

#### 5. State Manager
```javascript
class StateManager {
    constructor()
    updateFilters(filterState)
    updateSort(sortCriteria)
    getActiveFilters()
    resetFilters()
}
```

## Data Models

### Bookmark Object
```javascript
{
    url: string,           // Required: The bookmark URL
    title: string,         // Required: Display title
    description: string,   // Required: Description text
    tags: string[],        // Required: Array of tag strings
    dateAdded: string,     // Required: ISO 8601 date string
    favorite: boolean      // Required: Favorite status
}
```

### Filter State
```javascript
{
    tags: string[],        // Selected tag filters (AND logic)
    favorites: boolean,    // Show only favorites
    search: string,        // Search text
    sort: string          // Sort criteria
}
```

### Tag Summary
```javascript
{
    [tagName: string]: number  // Tag name to count mapping
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all identified properties, several can be consolidated:
- Properties 3.1-3.5 (sorting) can be combined into a comprehensive sorting property
- Properties 4.4-4.5 (icon display) can be combined into a single icon rendering property
- Properties 2.2-2.3 (tag filtering) represent the same underlying filtering logic

### Core Properties

**Property 1: Complete bookmark rendering**
*For any* set of bookmarks, when rendered, each bookmark should display all required fields: title, description, tags, dateAdded, and favorite status
**Validates: Requirements 1.3**

**Property 2: Bookmark count accuracy**
*For any* set of bookmarks, the displayed count should equal the actual number of bookmarks in the set
**Validates: Requirements 1.5**

**Property 3: Tag extraction and counting**
*For any* set of bookmarks, the tag list should contain all unique tags with accurate counts matching their occurrence in the bookmark set
**Validates: Requirements 2.1**

**Property 4: Tag filtering correctness**
*For any* set of bookmarks and any combination of selected tags, the filtered results should contain only bookmarks that have ALL selected tags
**Validates: Requirements 2.2, 2.3**

**Property 5: Filter state indication**
*For any* active filter state, the UI should visually indicate which filters are currently applied
**Validates: Requirements 2.4, 4.2**

**Property 6: Filter clearing round-trip**
*For any* bookmark set, applying filters then clearing all filters should return to the original complete set
**Validates: Requirements 2.5, 4.3**

**Property 7: Sorting correctness**
*For any* set of bookmarks and any sort criteria, the sorted results should be in the correct order according to the specified criteria
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

**Property 8: Favorites filtering**
*For any* set of bookmarks, when favorites filter is active, only bookmarks with favorite=true should be displayed
**Validates: Requirements 4.1**

**Property 9: Icon rendering consistency**
*For any* bookmark, the displayed icon should match the favorite status (star for favorites, empty star for non-favorites)
**Validates: Requirements 4.4, 4.5**

**Property 10: Search filtering**
*For any* search text and bookmark set, results should contain only bookmarks where the search text appears in title or description (case-insensitive)
**Validates: Requirements 5.1, 5.2**

**Property 11: Search clearing round-trip**
*For any* bookmark set, applying search then clearing search should return to the original complete set
**Validates: Requirements 5.3**

**Property 12: Combined filter logic**
*For any* combination of active filters (tags, favorites, search), the results should satisfy ALL active filter conditions simultaneously
**Validates: Requirements 5.4**

**Property 13: Data parsing robustness**
*For any* valid bookmarks.js file, the system should successfully parse and load all bookmark objects with all expected fields
**Validates: Requirements 8.1, 8.2**

**Property 14: Date formatting consistency**
*For any* valid dateAdded field, the system should display it in a consistent, human-readable format
**Validates: Requirements 8.3**

**Property 15: Tag array processing**
*For any* bookmark with a tags array, the system should correctly process and display all tags as individual filterable items
**Validates: Requirements 8.4**

## Error Handling

### Data Loading Errors
- **Missing bookmarks.js**: Display user-friendly message with instructions
- **Invalid JSON**: Show parsing error with guidance
- **Empty data**: Handle gracefully with empty state message
- **Malformed bookmarks**: Skip invalid entries, log warnings

### Runtime Errors
- **Filter failures**: Reset to safe state, show error message
- **Sort failures**: Fall back to default sort order
- **Rendering errors**: Show partial results where possible

### Progressive Enhancement Fallbacks
- **No JavaScript**: Show all bookmarks in static HTML
- **JavaScript errors**: Degrade gracefully to basic functionality
- **CSS failures**: Maintain readable text-based layout

## Testing Strategy

### Unit Testing Approach
- Test individual functions with specific examples
- Verify error handling with malformed inputs
- Test edge cases like empty data sets
- Validate HTML structure and CSS classes

### Property-Based Testing Approach
- Use **fast-check** library for JavaScript property-based testing
- Generate random bookmark datasets for comprehensive testing
- Test filtering, sorting, and search with varied inputs
- Verify UI state consistency across operations
- Run minimum 100 iterations per property test

**Property-based testing requirements:**
- Each property test must run at least 100 iterations
- Tests must be tagged with comments referencing design properties
- Tag format: `**Feature: static-bookmarks-viewer, Property {number}: {property_text}**`
- Each correctness property implemented by exactly one property-based test

### Integration Testing
- Test complete user workflows (filter → sort → search)
- Verify data loading from actual bookmarks.js files
- Test responsive behavior across viewport sizes
- Validate accessibility features

### Manual Testing
- Cross-browser compatibility testing
- Mobile device testing
- Accessibility testing with screen readers
- Performance testing with large bookmark sets

## Performance Considerations

### Loading Performance
- Single HTML file minimizes HTTP requests
- Embedded CSS and JavaScript eliminate additional requests
- Bookmarks.js loaded asynchronously to prevent blocking

### Runtime Performance
- Efficient filtering algorithms using native array methods
- Debounced search input to prevent excessive filtering
- Virtual scrolling for large bookmark sets (if needed)
- Minimal DOM manipulation during updates

### Memory Management
- Avoid memory leaks in event listeners
- Efficient data structures for filtering operations
- Cleanup of temporary objects during operations

## Accessibility

### Semantic HTML
- Proper heading hierarchy
- Meaningful link text
- Form labels and descriptions
- ARIA attributes where needed

### Keyboard Navigation
- Tab order follows logical flow
- All interactive elements keyboard accessible
- Focus indicators clearly visible
- Keyboard shortcuts for common actions

### Screen Reader Support
- Alt text for icons and images
- Status announcements for filter changes
- Descriptive text for bookmark counts
- Proper landmark regions

## Browser Compatibility

### Target Browsers
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

### Fallback Support
- CSS Grid with flexbox fallback
- Modern JavaScript with polyfill considerations
- Progressive enhancement for older browsers

## Future Enhancements

### Potential Additions
- Export functionality (JSON, CSV)
- Bookmark editing capabilities
- Drag-and-drop reordering
- Bulk operations (delete, tag modification)
- Theme customization
- Keyboard shortcuts
- URL sharing with filter state

### Integration Opportunities
- Browser extension integration
- Sync with Flask application
- Import from browser bookmarks
- Integration with bookmark services