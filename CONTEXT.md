# Bookmarks

A personal semantic recall store: saving a URL keeps it, each item is summarised by an LLM, and an agent is the primary way to find it again. Two parts: the store, which holds items and finds them, and ingestion, which turns submissions into items.

## The store

**Item**:
One kept URL and everything the store knows about it. Identified by its URL with tracking parameters and the fragment removed, so saving the same page again finds the existing item. An item exists only once it has a summary.
_Avoid_: Bookmark (for the record), entry, link

**Type**:
The single kind of thing an item points at. An open list: base types (article, repo, docs, product, discussion, media) plus any the summariser has adopted; the operator can merge two types into one. A merged-away type becomes an alias of the type it was merged into, so it is never adopted again.
_Avoid_: Category, kind, link type

**Summary**:
The prose account of what an item says, written lede-first so its first sentence stands alone; the only record of the item's content.
_Avoid_: Description, gist, abstract

**Entities**:
The specific named things an item mentions — people, organisations, tools, projects, publications, and named techniques or terms of art (e.g. CRDT, event sourcing) — specific to that item, not drawn from a shared vocabulary. General topics (e.g. system design) are not entities.
_Avoid_: Tags, keywords, concepts

**Provenance**:
Which CLI, model, and prompt version wrote an item's summary, and when.
_Avoid_: Metadata, source

**Note**:
An optional line the user writes when saving a URL, saying why it was kept; the user's own words, carried from the submission onto the item and kept apart from the summary.
_Avoid_: Comment, annotation, reason

**Search**:
Finding items from a loosely worded description or an exact term: a keyword match and a meaning match, ranked together. Filters (type, domain, saved time) narrow which items are considered; there is no relevance cutoff.
_Avoid_: Query, lookup, recall

## Ingestion

**Submission**:
A URL sent to be kept, with whatever the sender supplied (rendered page, note), waiting to become an item. Identified by its URL, like the item it becomes; it ends when the item exists.
_Avoid_: Job, queue entry, request

A submission for a URL that already has an item is a **refresh**: the operator asked for a fresh summary. It runs through the same stages, rewrites the item's summary and provenance in place (saved time and Note stay), and if it fails it just goes away, leaving the old summary.

**Capture surface**:
A way of sending a submission: the Firefox extension, the iOS Shortcut, or the save tool on the MCP server. Each sends a URL, optionally with the rendered page and a note.
_Avoid_: Capture client, client, integration

**Source text**:
The readable text the retrieving stage obtains for a submission (fetched server-side or sent by a capture surface as rendered HTML); kept only until the submission becomes an item, then discarded.
_Avoid_: Content, body, extracted text

**Stage**:
One step a submission goes through on its way to becoming an item, run later in bulk rather than at save time: retrieving (obtaining the source text), then summarising.
_Avoid_: Step, phase, job; acquiring (for retrieving)

**Status**:
Where a saved URL stands as the user sees it: pending (a submission waiting for a stage), failed (a submission with a reason naming the stage that failed; saving the URL again retries it), or summarised (an item). A failure is never stored as a summary.
_Avoid_: State, processed flag
