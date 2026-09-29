# Bookmarks

A personal semantic recall store: saving a URL keeps it, each item is summarised by an LLM, and an agent is the primary way to find it again.

## Language

**Item**:
One saved URL and everything the store knows about it.
_Avoid_: Bookmark (for the record), entry, link

**Capture surface**:
A way of saving an item: the Firefox extension, the iOS Shortcut, or the save tool on the MCP server. Each sends a URL, optionally with the rendered page and a note.
_Avoid_: Capture client, client, integration

**Type**:
The single kind of thing an item points at. An open list: base types (article, repo, docs, product, discussion, media) plus any the summariser has adopted; the operator can merge two types into one.
_Avoid_: Category, kind, link type

**Source text**:
The readable text obtained for an item at save time (fetched server-side or sent by a capture surface as rendered HTML); transient — used to write the summary, never kept.
_Avoid_: Content, body, extracted text

**Summary**:
The prose account of what an item says, written lede-first so its first sentence stands alone; the only record of the item's content.
_Avoid_: Description, gist, abstract

**Entities**:
The specific named things an item mentions — people, organisations, tools, projects, publications, and named techniques or terms of art (e.g. CRDT, event sourcing) — specific to that item, not drawn from a shared vocabulary. General topics (e.g. system design) are not entities.
_Avoid_: Tags, keywords, concepts

**Status**:
Where an item stands in summarisation: pending, summarised, or failed (with a reason). A failed item has no summary; a failure is never stored as one.
_Avoid_: State, processed flag

**Provenance**:
Which CLI, model, and prompt version wrote an item's summary, and when.
_Avoid_: Metadata, source

**Note**:
An optional line the user writes when saving an item, saying why it was kept; the user's own words, kept apart from the summary.
_Avoid_: Comment, annotation, reason
