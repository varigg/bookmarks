# Quick Reference: Bookmark Import with LLM

> **For comprehensive configuration details, see [LLM Configuration Guide](LLM_CONFIGURATION.md)**

## Basic Import (No API Key Needed)

```bash
# Add bookmarks with "unread" description
uv run python tools/add_bookmarks_from_urls.py urls.txt

# Preview without saving
uv run python tools/add_bookmarks_from_urls.py urls.txt --dry-run
```

## LLM-Generated Descriptions

### First Time Setup

```bash
# 1. Install dependencies
uv add requests beautifulsoup4 lxml

# 2. Set API key (PowerShell)
$env:PERPLEXITY_API_KEY = "pplx-your-key-here"

# 3. Test
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions --dry-run
```

### Regular Usage

```bash
# Test your LLM configuration first
uv run python tools/add_bookmarks_from_urls.py --test

# Default: Perplexity with HTML extraction (fastest, works well for most sites)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Use Markdown extraction (better for technical docs, preserves structure)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --content-format markdown

# Use Perplexity MCP (advanced, requires additional setup)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --provider perplexity-mcp

# Preview first (recommended - no API calls made)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --dry-run
```

> **Note:** The `--provider` and `--content-format` parameters mirror the `BOOKMARKS_LLM_PROVIDER` and `BOOKMARKS_LLM_CONTENT_FORMAT` environment variables. See [LLM Configuration Guide](LLM_CONFIGURATION.md) for details.

## URL File Format

```
# Comments start with #
https://example.com/article1
https://github.com/project
https://news.ycombinator.com/item?id=12345
```

## Cost Estimation

| URLs | Estimated Cost | Within $5 Credit? |
| ---- | -------------- | ----------------- |
| 10   | $0.05          | ✅ Yes            |
| 50   | $0.25          | ✅ Yes            |
| 100  | $0.50          | ✅ Yes            |
| 500  | $2.50          | ✅ Yes            |
| 1000 | $5.00          | ✅ Yes (exactly)  |
| 2000 | $10.00         | ❌ No ($5 extra)  |

_Estimates based on sonar model. Actual costs may vary._

## Common Commands

```bash
# Check what would be added (no API calls)
uv run python tools/add_bookmarks_from_urls.py urls.txt --dry-run

# Add with LLM descriptions
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Process first 10 URLs only
head -10 large_list.txt | uv run python tools/add_bookmarks_from_urls.py - --generate-descriptions
```

## Troubleshooting

| Problem            | Solution                                          |
| ------------------ | ------------------------------------------------- |
| "API key required" | Set `PERPLEXITY_API_KEY` environment variable     |
| "Module not found" | Run `uv add requests beautifulsoup4 lxml`         |
| Rate limited       | Script handles automatically, wait a moment       |
| High costs         | Use `--dry-run` first, process in smaller batches |

## Output Example

```
✓ Initialized Perplexity client

[1/3] 🔍 Generating description for: https://github.com/python/cpython
         ✓ Title: Python Programming Language - Official Repository...
[2/3] 🔍 Generating description for: https://example.com
         ✓ Title: Example Domain for Documentation...
[3/3] ⊘ Skipping (already exists): https://duplicate.com

============================================================
Summary:
  Added: 2
  Skipped (duplicates): 1
  Total URLs processed: 3

LLM Usage Statistics:
  API Requests: 2
  Total Tokens: 300
  Estimated Cost: $0.0100
  (Your Pro subscription includes $5/month in credits)
============================================================
```

## See Also

- **[LLM Configuration Guide](LLM_CONFIGURATION.md)** - Complete guide to LLM service configuration
- **[MCP Guide](MCP_GUIDE.md)** - Model Context Protocol setup details
- **[LLM Setup Guide](SETUP_STAGE2.md)** - Advanced setup options
- **[ADDING_BOOKMARKS.md](ADDING_BOOKMARKS.md)** - Detailed documentation on adding bookmarks
- Get API key: https://www.perplexity.ai/settings/api
