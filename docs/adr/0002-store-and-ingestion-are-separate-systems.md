# The store and ingestion are separate systems

Bookmarks is two systems. The store holds items and finds them: records, Type, search and embeddings. Ingestion turns submissions into items: the drain, lifecycle policy, retrieving and summarising. Items enter the store only through its insert; ingestion is the first producer, and any later system that adds items uses the same entry point. The legacy importer (#33) is not one: it creates submissions with their original saved dates, so its URLs are summarised fresh. An item exists only once it is summarised, so pending and failed are states of a submission, never of an item. Before this, a pending item had exactly one `queue` row and the two had to change together. The domain's record was tangled with the drain's working state, and an item could sit stranded as pending with no queue row and nothing to notice it.

## Decisions

- **Insert only.** The store's insert refuses a URL that already has an item; the producer decides what that means. Resummarising (#29) uses a separate replace, which keeps the item's note and saved time.
- **Failure stays on the submission.** A submission that cannot become an item is marked failed with a reason naming the stage. Saving the URL again resets it.
- **The URL is the handle.** Submissions and items have separate ids. A save answers with the URL, its status and the saved time; an item id exists once the item does.
- **Embedding belongs to the store.** A vector is a search index derived from an item, like the full-text index. The store embeds any item lacking a vector for the current model, whoever produced it, so Stages are retrieving then summarising.
- **Ingestion lives in `bookmarks.ingest`.** A test enforces the direction: ingestion reaches the store only through its public functions, and nothing in the store imports `bookmarks.ingest`. The composition roots wire both.

## Considered Options

- **The store writes item and queue rows together** (the original #36 plan). Rejected: it puts the drain's working state inside the record owner, so the store would know how ingestion works.
- **A failed submission becomes a failed item.** Rejected: it keeps a status column on items for one case, and failed rows would need excluding from every store read.
- **Upsert on insert.** Rejected: a producer could silently overwrite a fresher summary, and resummarising needs different rules (keep note and saved time) anyway.
- **Ingestion embeds before inserting.** Rejected: every other producer would have to embed too, and a model change re-embeds outside ingestion anyway.
- **A flat layout with the boundary kept by convention, or two installable packages.** Rejected: the first has no gate, and the second costs a workspace and two `pyproject.toml` files for one person's app.

## Consequences

- Saving checks the store for an item first, then ingestion's own submissions; "already saved" covers both.
- Inserting an item with a Type the store has not seen adopts it. The summariser reads the type list from the store.
- The insert takes the saved time from its caller, so tests seed items at chosen times and the `Clock` protocol can go (#36).
- ADR 0001 still holds; its "kept only until the item is summarised" now reads "until the submission becomes an item".
