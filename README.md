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
uv run bookmarks resummarise --stale  # queue fresh summaries (also --item, --type, --domain, --limit)
uv run bookmarks mcp          # MCP server over stdio
uv run bookmarks retrieve URL # print the source text the retrieving stage would produce
```

The store is one SQLite file at `$XDG_DATA_HOME/bookmarks/bookmarks.db`
(override with `BOOKMARKS_DB`).

## Deploying

Production runs the `bookmarks` uv tool at `~/.local/bin/bookmarks`, never a
clone (ADR 0003). From any clone on thunderbird:

```sh
scripts/deploy.sh          # deploy origin/main
scripts/deploy.sh <ref>    # deploy another commit
```

It gates the commit in a clean worktree, builds its wheel and lock-pinned
constraints into `~/.local/share/bookmarks/releases/<sha>/`, then, holding the
drain's lock, installs it, installs `deploy/bookmarks-web.service`, restarts
the web server and probes the console, the capture route and the MCP tools
(`scripts/probe.py`). A failed probe reinstalls the previous release. Exit 0:
live; 1: refused, nothing changed; 2: reverted; 3: no probed release is live.

`deploy/crontab` holds the drain + embed and backup entries, installed once
with `crontab -e`. The cron log directory `~/.local/state/bookmarks/` must exist.

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
claude mcp add --scope user bookmarks -- /home/varigg/.local/bin/bookmarks mcp
```

From another machine, wrap the same command in SSH (stdio passes through):

```sh
claude mcp add --scope user bookmarks -- \
  ssh thunderbird /home/varigg/.local/bin/bookmarks mcp
```

## Configuration

Non-secret settings live in `~/.config/bookmarks/env` (template:
`deploy/env.example`), read by the cron entries and by the systemd unit.

Required for `backup`: `BOOKMARKS_BACKUP_DIR` (an existing directory; if it
is missing, nothing is written and `BOOKMARKS_ALERT_TO` is emailed) and
`BOOKMARKS_ALERT_TO`.

Optional environment variables: `BOOKMARKS_OLLAMA_URL` (default
`http://127.0.0.1:11434`, Ollama's own address), `BOOKMARKS_DB`, `BOOKMARKS_HOST`,
`BOOKMARKS_PORT`, `BOOKMARKS_CLAUDE` (CLI path), `BOOKMARKS_SUMMARISER_MODEL`
(default `claude-sonnet-5-5`), `BOOKMARKS_SUMMARISER_TIMEOUT`,
`BOOKMARKS_SOURCE_CAP_CHARS` (~25K tokens), `BOOKMARKS_FETCH_TIMEOUT`,
`BOOKMARKS_GITHUB_TOKEN`, `BOOKMARKS_EMBED_MODEL` (default
`nomic-embed-text`; changing it re-embeds everything on the next embed run),
and `BOOKMARKS_EMBED_TIMEOUT`.
