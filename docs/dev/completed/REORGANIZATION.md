# Project Reorganization Summary

All utility scripts have been moved to the `tools/` directory for better organization.

## New Structure

```
bookmarks/
├── bookmarks/              # Main application package
│   ├── __init__.py
│   ├── routes.py
│   ├── model.py
│   └── templates/
├── tools/                  # ✨ NEW: Utility scripts
│   ├── README.md          # Documentation for all tools
│   ├── add_bookmarks_from_urls.py
│   ├── check_urls.py
│   ├── convert_timestamps.py
│   ├── find_unread.py
│   ├── get_all_tags.py
│   ├── perplexity_client.py
│   ├── perplexity_mcp_client.py
│   ├── test_perplexity.py
│   ├── update_bookmarks.py
│   └── update_tags.py
├── tests/                  # Test files
├── QUICKSTART_LLM.md      # Updated with new paths
├── SETUP_STAGE2.md        # Updated with new paths
├── ADDING_BOOKMARKS.md    # Updated with new paths
├── MCP_GUIDE.md           # Updated with new paths
└── README.md              # Main project README
```

## What Changed

### Files Moved to `tools/`

1. **Import/Export:**
   - `add_bookmarks_from_urls.py` - Bulk import with LLM descriptions

2. **Analysis:**
   - `find_unread.py` - Find unread bookmarks
   - `get_all_tags.py` - List all tags
   - `check_urls.py` - Validate URLs

3. **Maintenance:**
   - `update_tags.py` - Rename/convert tags
   - `update_bookmarks.py` - Batch updates
   - `convert_timestamps.py` - Timestamp conversion

4. **Development:**
   - `test_perplexity.py` - Test Perplexity integration
   - `perplexity_client.py` - Direct API client
   - `perplexity_mcp_client.py` - MCP client

### Documentation Updated

All documentation files have been updated to use the new `tools/` prefix:

- ✅ `QUICKSTART_LLM.md`
- ✅ `SETUP_STAGE2.md`
- ✅ `ADDING_BOOKMARKS.md`
- ✅ `MCP_GUIDE.md`
- ✅ `tools/README.md` (new)

## Usage Examples

### Before (Old Paths)
```bash
uv run python add_bookmarks_from_urls.py urls.txt
uv run python find_unread.py
uv run python update_tags.py "old" "new"
```

### After (New Paths)
```bash
uv run python tools/add_bookmarks_from_urls.py urls.txt
uv run python tools/find_unread.py
uv run python tools/update_tags.py "old" "new"
```

## Benefits

1. **Better Organization**
   - Clear separation between app code and utility scripts
   - Easier to find tools
   - Cleaner project root

2. **Improved Documentation**
   - All tools documented in one place (`tools/README.md`)
   - Easier to discover available utilities

3. **Scalability**
   - Easy to add new tools
   - Clear structure for future growth

## Quick Reference

See `tools/README.md` for complete documentation of all available tools and common workflows.

### Most Common Commands

```bash
# Import bookmarks with AI descriptions
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Find unread bookmarks
uv run python tools/find_unread.py

# List all tags
uv run python tools/get_all_tags.py

# Rename a tag
uv run python tools/update_tags.py "old-tag" "new-tag"

# Test Perplexity integration
uv run python tools/test_perplexity.py --method both
```

---

**Note:** All existing functionality remains the same - only the file paths have changed!
