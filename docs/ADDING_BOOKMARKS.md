# Adding Bookmarks from URL Lists

This document explains how to use the `add_bookmarks_from_urls.py` script to bulk-add bookmarks.

## Stage 1: Basic Bookmark Import (✓ Implemented)

### Usage

```bash
# Basic import with 'unread' description
uv run python tools/add_bookmarks_from_urls.py urls.txt

# Dry run to preview what would be added
uv run python tools/add_bookmarks_from_urls.py urls.txt --dry-run
```

### URL File Format

Create a text file with one URL per line:

```
# Lines starting with # are comments
https://example.com/article1
https://github.com/some-project
https://news.ycombinator.com/item?id=12345
```

### What It Does

- Reads URLs from a text file
- Creates bookmark entries with:
  - URL as the title (temporary)
  - Description: "Imported from URL list. Status: unread"
  - Tag: `unread`
  - Current timestamp
- Skips duplicate URLs automatically
- Generates sequential numeric IDs

---

## Stage 2: LLM-Generated Descriptions (TODO)

### Overview

Stage 2 will use LLMs (Perplexity or Copilot) to automatically generate:
- Meaningful titles
- Descriptive summaries
- Suggested tags (optional enhancement)

### Planned Usage

```bash
# Generate descriptions with Perplexity (default)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Use Copilot instead
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --provider copilot

# Preview with dry run
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --dry-run
```

### Implementation Options

#### Option 1: Perplexity with MCP (Recommended)

Perplexity has a web search MCP server that can fetch and summarize web pages.

**Advantages:**
- Built-in web search capability
- Can access current page content
- Good for generating accurate descriptions

**Implementation Steps:**
1. Install Perplexity MCP server
2. Use MCP to fetch page content
3. Generate summary using Perplexity API
4. Extract title from HTML or use generated title

**Code Structure:**
```python
def generate_description_with_perplexity(url):
    # 1. Use MCP to search/fetch page
    # 2. Call Perplexity API with page content
    # 3. Return {title, description}
    pass
```

#### Option 2: GitHub Copilot API

Use Copilot's API to generate descriptions.

**Advantages:**
- Already have access
- Good at understanding code repositories

**Limitations:**
- May need to fetch page content separately
- Better for code-related URLs

**Implementation Steps:**
1. Fetch page HTML/content (using requests)
2. Extract text/metadata
3. Call Copilot API for summarization
4. Parse response

#### Option 3: Hybrid Approach

- Use Perplexity MCP for general web pages
- Use Copilot for GitHub/code URLs
- Auto-detect URL type

### Required Dependencies

```toml
# Add to pyproject.toml
[project.dependencies]
# For web scraping
requests = "^2.31.0"
beautifulsoup4 = "^4.12.0"

# For Perplexity (if using direct API)
# perplexity-sdk = "^x.x.x"  # Check latest version

# For MCP integration
# mcp-client = "^x.x.x"  # If needed
```

### Environment Variables

```bash
# .env file
PERPLEXITY_API_KEY=your_key_here
# or
COPILOT_API_KEY=your_key_here
```

### Prompt Template

For LLM summarization:

```
Given this URL and its content, generate:
1. A concise, descriptive title (max 100 chars)
2. A 2-3 sentence summary of what the page is about

URL: {url}
Content: {page_content}

Format your response as JSON:
{
  "title": "...",
  "description": "..."
}
```

### Error Handling

The script should gracefully handle:
- URLs that can't be fetched (404, timeout)
- LLM API failures
- Rate limiting
- Malformed responses

Fallback: Use Stage 1 basic entry if LLM fails.

### Rate Limiting

To avoid hitting API limits:
- Add delay between requests (e.g., 1-2 seconds)
- Batch process in chunks
- Show progress bar for large lists
- Cache results to avoid re-processing

### Future Enhancements

1. **Tag Suggestion**: Have LLM suggest relevant tags
2. **Content Extraction**: Better extraction of article text
3. **Batch Processing**: Process multiple URLs in parallel
4. **Resume Support**: Save progress and resume if interrupted
5. **Quality Check**: Validate generated descriptions
6. **Custom Prompts**: Allow user-defined prompt templates

---

## Testing

### Stage 1 Test

```bash
# Create test file
echo "https://github.com/python/cpython" > test_urls.txt

# Dry run
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --dry-run

# Actual import
uv run python tools/add_bookmarks_from_urls.py test_urls.txt
```

### Stage 2 Test (Once Implemented)

```bash
# Test with a few URLs first
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions --dry-run

# If successful, run for real
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions
```

---

## Next Steps for Stage 2 Implementation

1. **Choose LLM Provider**: Decide between Perplexity MCP or Copilot
2. **Set Up Authentication**: Get API keys and configure
3. **Implement Web Fetching**: Add code to retrieve page content
4. **Implement LLM Integration**: Add API calls and response parsing
5. **Add Error Handling**: Robust fallbacks and retries
6. **Test Thoroughly**: Start with small batches
7. **Optimize**: Add rate limiting and progress indicators

Would you like me to implement Stage 2 with a specific provider?
