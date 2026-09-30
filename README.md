# bookmarks

A personal semantic recall store. Saving a URL keeps it; the drain summarises
each item with `claude -p`; an agent finds items again over MCP. The spec is
[#19](https://github.com/varigg/bookmarks/issues/19); vocabulary lives in
[`CONTEXT.md`](CONTEXT.md).

The pre-rebuild Flask app lives at commit `5fddc16`.

## Development

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Running

```sh
uv run bookmarks serve        # capture API on $BOOKMARKS_HOST:$BOOKMARKS_PORT (0.0.0.0:5000)
uv run bookmarks drain        # summarise queued items with `claude -p` (cron job)
```

The store is one SQLite file at `$XDG_DATA_HOME/bookmarks/bookmarks.db`
(override with `BOOKMARKS_DB`).

Deployment files (not installed until cutover) are in `deploy/`:
`bookmarks-web.service` is the systemd user unit for the web server;
`crontab` holds the drain entry (every 10 minutes).

## Capture API

`POST /api/items` with JSON `{"url": ..., "html"?: ..., "title"?: ..., "note"?: ...}`.
Replies `201` with `{"outcome": "saved", "message": "Saved", ...}` for a new
item, `200` with `"already_saved"` and `"Already saved on <date>"` for a
duplicate (plus `"; note not added"` when a note was supplied), `422` for an
invalid payload or a non-http(s) URL.
