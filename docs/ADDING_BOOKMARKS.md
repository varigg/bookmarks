# Adding Bookmarks from URL Lists

This document explains how to use the `add_bookmarks_from_urls.py` script to bulk-add bookmarks.

## Basic Import

Import bookmarks without LLM-generated descriptions:

```bash
# Basic import
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
  - Description: "Imported from URL list. Needs summary."
  - Tag: `unsummarized`
  - Current timestamp
- Skips duplicate URLs automatically
- Generates sequential numeric IDs

---

## LLM-Generated Descriptions

The script supports multiple LLM providers to automatically generate meaningful titles and descriptions.

### Usage

```bash
# Generate descriptions with Perplexity (default)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Use Perplexity MCP
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --provider perplexity-mcp

# Use Markdown content extraction
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --content-format markdown

# Test LLM configuration
uv run python tools/add_bookmarks_from_urls.py --test

# Preview with dry run
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --dry-run
```

### Configuration

Set environment variables to configure LLM behavior:

```bash
# Set LLM provider
export BOOKMARKS_LLM_PROVIDER=perplexity  # or: perplexity-mcp, openai, anthropic

# Set content extraction format
export BOOKMARKS_LLM_CONTENT_FORMAT=html  # or: markdown

# Set API key (depending on provider)
export PERPLEXITY_API_KEY=pplx-your-key
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
```

See `docs/LLM_CONFIGURATION.md` for complete setup instructions.

### Supported Providers

- **perplexity**: Direct Perplexity API with HTML/Markdown content extraction
- **perplexity-mcp**: Perplexity via Model Context Protocol (no separate content extraction)
- **openai**: OpenAI API (gpt-4o-mini model) with HTML/Markdown content extraction
- **anthropic**: Anthropic API (claude-3-5-haiku model) with HTML/Markdown content extraction
- **anthropic**: Anthropic API (placeholder)

### Content Extraction

- **html**: BeautifulSoup-based extraction (fast, lightweight)
- **markdown**: MarkItDown conversion (better content structure)

### What It Does

When generating descriptions, the script:

1. Fetches the page content (HTML or Markdown)
2. Calls the LLM provider to generate title and description
3. Creates bookmark with:
   - LLM-generated title
   - LLM-generated description
   - Tag: `summarized`
   - Current timestamp

### Error Handling

If LLM generation fails:

- Falls back to basic bookmark entry
- Tags with `unsummarized` for later processing
- Logs error for review

---

## Testing

```bash
# Create test file
echo "https://github.com/python/cpython" > test_urls.txt

# Test basic import
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --dry-run

# Test LLM configuration
uv run python tools/add_bookmarks_from_urls.py --test

# Test with LLM descriptions
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions --dry-run

# Actual import with descriptions
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions
```

---

## Batch Processing Workflow

For processing existing bookmarks without descriptions:

```bash
# 1. Find unsummarized bookmarks
uv run python tools/find_unsummarized.py --count 20 --json-output batch.json

# 2. Generate descriptions (manual step or custom script)
# Process URLs from batch.json with LLM

# 3. Update bookmarks
uv run python tools/update_bookmarks.py --json-file updates.json
```
