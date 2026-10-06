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
uv run bookmarks embed        # embed summarised items via local Ollama (cron job)
uv run bookmarks mcp          # MCP server over stdio
```

The store is one SQLite file at `$XDG_DATA_HOME/bookmarks/bookmarks.db`
(override with `BOOKMARKS_DB`).

Deployment files (not installed until cutover) are in `deploy/`:
`bookmarks-web.service` is the systemd user unit for the web server;
`crontab` holds the drain + embed entry (every 10 minutes). The cron log
directory `~/.local/state/bookmarks/` must exist.

## Capture API

`POST /api/items` with JSON `{"url": ..., "html"?: ..., "title"?: ..., "note"?: ...}`.
Replies `201` with `{"outcome": "saved", "message": "Saved", ...}` for a new
item, `200` with `"already_saved"` and `"Already saved on <date>"` for a
duplicate (plus `"; note not added"` when a note was supplied), `422` for an
invalid payload or a non-http(s) URL.

## MCP server

Tools: `search` (hybrid keyword + semantic; filters `types`, `domain`,
`saved_after`, `saved_before`, `status`; `limit` default 10, max 50).

Register it for every Claude Code session on thunderbird (user scope):

```sh
claude mcp add --scope user bookmarks -- \
  /snap/bin/uv --directory /home/varigg/code/bookmarks run --frozen --no-dev bookmarks mcp
```

From another machine, wrap the same command in SSH (stdio passes through):

```sh
claude mcp add --scope user bookmarks -- \
  ssh thunderbird /snap/bin/uv --directory /home/varigg/code/bookmarks run --frozen --no-dev bookmarks mcp
```

## Configuration

Environment variables, all optional: `BOOKMARKS_DB`, `BOOKMARKS_HOST`,
`BOOKMARKS_PORT`, `BOOKMARKS_CLAUDE` (CLI path), `BOOKMARKS_SUMMARISER_MODEL`
(default `claude-sonnet-5-5`), `BOOKMARKS_SUMMARISER_TIMEOUT`,
`BOOKMARKS_SOURCE_CAP_CHARS` (~25K tokens), `BOOKMARKS_FETCH_TIMEOUT`,
`BOOKMARKS_GITHUB_TOKEN`, `BOOKMARKS_EMBED_MODEL` (default
`nomic-embed-text`; changing it re-embeds everything on the next embed run),
`BOOKMARKS_OLLAMA_URL` (default `http://127.0.0.1:11434`),
and `BOOKMARKS_EMBED_TIMEOUT`.
