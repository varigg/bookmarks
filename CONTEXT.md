# Bookmarks

A personal semantic recall store: saving a URL keeps it, each item is summarised by an LLM, and an agent is the primary way to find it again.

## Language

**Item**:
One saved URL and everything the store knows about it. Identified by its URL with tracking parameters and the fragment removed, so saving the same page again finds the existing item.
_Avoid_: Bookmark (for the record), entry, link

**Capture surface**:
A way of saving an item: the Firefox extension, the iOS Shortcut, or the save tool on the MCP server. Each sends a URL, optionally with the rendered page and a note.
_Avoid_: Capture client, client, integration

**Type**:
The single kind of thing an item points at. An open list: base types (article, repo, docs, product, discussion, media) plus any the summariser has adopted; the operator can merge two types into one. A merged-away type becomes an alias of the type it was merged into, so it is never adopted again.
_Avoid_: Category, kind, link type

**Source text**:
The readable text the retrieving stage obtains for an item (fetched server-side or sent by a capture surface as rendered HTML); kept only until the item is summarised, then discarded.
_Avoid_: Content, body, extracted text

**Stage**:
One step of processing an item goes through after it is saved, run later in bulk rather than at save time: retrieving (obtaining the source text), then summarising, then embedding.
_Avoid_: Step, phase, job; acquiring (for retrieving)

**Summary**:
The prose account of what an item says, written lede-first so its first sentence stands alone; the only record of the item's content.
_Avoid_: Description, gist, abstract

**Entities**:
The specific named things an item mentions — people, organisations, tools, projects, publications, and named techniques or terms of art (e.g. CRDT, event sourcing) — specific to that item, not drawn from a shared vocabulary. General topics (e.g. system design) are not entities.
_Avoid_: Tags, keywords, concepts

**Status**:
Where an item stands as the user sees it: pending (not yet summarised, whichever stage it is waiting for), summarised, or failed (with a reason naming the stage that failed). A summarised item with no embedding yet is still summarised. A failed item has no summary; a failure is never stored as one.
_Avoid_: State, processed flag

**Provenance**:
Which CLI, model, and prompt version wrote an item's summary, and when.
_Avoid_: Metadata, source

**Note**:
An optional line the user writes when saving an item, saying why it was kept; the user's own words, kept apart from the summary.
_Avoid_: Comment, annotation, reason

**Search**:
Finding items from a loosely worded description or an exact term: a keyword match and a meaning match, ranked together. Filters (type, domain, saved time, status) narrow which items are considered; there is no relevance cutoff.
_Avoid_: Query, lookup, recall
