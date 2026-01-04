# Bookmarks Tools

Utility scripts for managing and enhancing the bookmarks application.

## Import & Export Tools

### `add_bookmarks_from_urls.py`

Import bookmarks from a list of URLs with optional LLM-generated descriptions.

```bash
# Basic import without LLM descriptions
uv run python tools/add_bookmarks_from_urls.py urls.txt

# With LLM-generated descriptions (default: Perplexity + HTML)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# With Markdown content extraction
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --content-format markdown

# With Perplexity MCP
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --provider perplexity-mcp

# Test LLM configuration
uv run python tools/add_bookmarks_from_urls.py --test

# Preview without saving
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --dry-run
```

**Features:**

- Automatic duplicate detection
- LLM-powered title and description generation
- Multiple LLM providers (Perplexity, Perplexity MCP, OpenAI, Anthropic)
- Content extraction (HTML or Markdown)
- Cost tracking and estimation
- Progress indicators
- Dry-run mode

**Documentation:** See `QUICKSTART_LLM.md` and `docs/LLM_CONFIGURATION.md`

### `static-bookmarks.html`

Standalone HTML viewer for browsing bookmarks without any server dependencies.

**Usage:**

1. Open `tools/static-bookmarks.html` in any web browser
2. The viewer automatically loads `bookmarks.js` from the project root
3. Use the sidebar to filter by tags, favorites, or search
4. Sort bookmarks by date, alphabetically, or favorites-first

**Features:**

- Zero dependencies (pure HTML/CSS/JavaScript)
- Responsive design (mobile, tablet, desktop)
- Real-time search and filtering
- Multiple sort options
- Accessibility features (ARIA labels, keyboard navigation)
- Print-friendly styles
- Works offline

**Use Cases:**

- Quick bookmark browsing without starting the server
- Sharing bookmarks as a static file
- Backup/archive viewing
- Testing bookmark data structure

---

## Analysis Tools

### `find_unsummarized.py`

Find and list bookmarks that need LLM-generated summaries (tagged with 'unsummarized').

```bash
# Show next 10 unsummarized bookmarks
uv run python tools/find_unsummarized.py

# Show next 20 with detailed info
uv run python tools/find_unsummarized.py --count 20 --detailed

# Export to JSON for batch processing
uv run python tools/find_unsummarized.py --count 50 --json-output unsummarized.json
```

**Use Case:** Used with `update_bookmarks.py` to identify bookmarks needing descriptions.

### `get_all_tags.py`

List all unique tags used across bookmarks.

```bash
uv run python tools/get_all_tags.py
```

---

## Maintenance Tools

### `update_tags.py`

Convert or rename tags across all bookmarks.

```bash
# Dry run to preview changes
uv run python tools/update_tags.py "old-tag" "new-tag" --dry-run

# Actually update tags
uv run python tools/update_tags.py "old-tag" "new-tag"
```

**Example:**

```bash
# Rename AI-generated summary tags
uv run python tools/update_tags.py "Summarized by Gemini" "AI Summary"
```

### `update_bookmarks.py`

Batch update bookmark properties from JSON file. Typically used after `find_unsummarized.py`.

```bash
# Update bookmarks with LLM-generated descriptions
uv run python tools/update_bookmarks.py --json-file updates.json
```

**Features:**

- Updates title, description, and tags
- Removes 'unsummarized' tag
- Adds 'summarized' timestamp

---

## Common Workflows

### Bulk Import New Bookmarks with LLM Descriptions

```bash
# 1. Create URL list
cat > new_bookmarks.txt << EOF
https://example.com/article1
https://example.com/article2
EOF

# 2. Test LLM configuration
uv run python tools/add_bookmarks_from_urls.py --test

# 3. Preview import
uv run python tools/add_bookmarks_from_urls.py new_bookmarks.txt --generate-descriptions --dry-run

# 4. Import with descriptions
uv run python tools/add_bookmarks_from_urls.py new_bookmarks.txt --generate-descriptions
```

### Generate Summaries for Existing Bookmarks

```bash
# 1. Find bookmarks needing summaries
uv run python tools/find_unsummarized.py --count 20 --json-output batch.json

# 2. Process with LLM (manual step or custom script)
# ... generate descriptions for URLs in batch.json ...

# 3. Update bookmarks with new descriptions
uv run python tools/update_bookmarks.py --json-file updates.json
```

### Clean Up Tags

```bash
# 1. See all tags
uv run python tools/get_all_tags.py

# 2. Rename tags
uv run python tools/update_tags.py "old-tag" "new-tag" --dry-run
uv run python tools/update_tags.py "old-tag" "new-tag"
```

---

## Testing Tools

### `test_perplexity.py`

Test Perplexity API configuration.

```bash
export PERPLEXITY_API_KEY=pplx-your-key
uv run python tools/test_perplexity.py
```

### `test_openai.py`

Test OpenAI API configuration.

```bash
export OPENAI_API_KEY=sk-your-key
uv run python tools/test_openai.py
```

### `test_anthropic.py`

Test Anthropic API configuration.

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
uv run python tools/test_anthropic.py
```

---

## Configuration

Most tools work with the base installation. For LLM features, see `docs/LLM_CONFIGURATION.md` for detailed setup instructions.

**Quick Setup:**

```bash
# Set LLM provider (perplexity, perplexity-mcp, openai, anthropic)
export BOOKMARKS_LLM_PROVIDER=perplexity

# Set content format (html, markdown)
export BOOKMARKS_LLM_CONTENT_FORMAT=html

# Set API key (depending on provider)
export PERPLEXITY_API_KEY=pplx-your-key
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
```

---

## See Also

- `docs/QUICKSTART_LLM.md` - Quick reference for LLM features
- `docs/LLM_CONFIGURATION.md` - Complete LLM setup guide
- `docs/SETUP_STAGE2.md` - LLM setup instructions
- `docs/MCP_GUIDE.md` - Understanding MCP protocol
