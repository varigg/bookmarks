# Future Enhancements

## LLM Integration
- [ ] **Automatically generate tags**: The LLM should suggest relevant tags based on the content.
- [ ] **Generalize Markdown Conversion**: Decouple the markdown conversion logic (MarkItDown) so it can be used with any LLM client, not just Perplexity.
- [ ] **Rename Factory**: Rename `perplexity_factory.py` to `llm_client_factory.py` to support future providers (e.g., Copilot, OpenAI).

## Search
- [ ] **Improve Search**: Expand search to include Title and URL, not just Description.

## Import/Export
- [ ] **Instapaper Import**: Parse Instapaper CSV/HTML exports to extract original URLs and import bookmarks in bulk.

## UI/UX
- [ ] **Pagination**: Add pagination for better performance with large datasets (currently deferred).
