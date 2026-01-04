# Configuration Guide

The bookmarks application uses simple environment variables for configuration, making it easy to deploy and customize.

## Configuration Options

All configuration is done through environment variables:

| Variable                       | Default          | Description                                                                                                    |
| ------------------------------ | ---------------- | -------------------------------------------------------------------------------------------------------------- |
| `BOOKMARKS_DATA_DIR`           | `.`              | Base directory for `bookmarks.js` and backups (the service install binds `/srv/bookmarks-data` from the host). |
| `BOOKMARKS_DATA_SOURCE`        | `bookmarks.js`   | Path to the bookmarks data file                                                                                |
| `BOOKMARKS_SECRET_KEY`         | (auto-generated) | Flask secret key for sessions                                                                                  |
| `BOOKMARKS_DEBUG`              | `false`          | Enable debug mode (`true`/`false`)                                                                             |
| `BOOKMARKS_PORT`               | `5001`           | Port number for the server                                                                                     |
| `BOOKMARKS_BACKUP_ENABLED`     | `true`           | Enable automatic backups on startup                                                                            |
| `BOOKMARKS_BACKUP_DIR`         | `backup`         | Directory to store backup files                                                                                |
| `BOOKMARKS_BACKUP_COUNT`       | `5`              | Number of backups to keep (older ones are deleted)                                                             |
| `BOOKMARKS_LLM_PROVIDER`       | `perplexity`     | LLM provider (perplexity/openai/anthropic)                                                                     |
| `BOOKMARKS_LLM_CONTENT_FORMAT` | `markdown`       | Content extraction format (html/markdown)                                                                      |

`BOOKMARKS_DATA_DIR` defaults to the current directory for local development, but `make service-install` overrides it to `/srv/bookmarks-data` and creates that directory (plus a `backup/` subfolder) on the host before starting the container. Update the variable to point somewhere else if you want your data to live in a different location.

## Usage Examples

### Basic Usage (Default Settings)

No configuration needed! Just run:

```bash
uv run flask run
```

This uses `bookmarks.js` in the project directory.

### Custom Data File

```bash
export BOOKMARKS_DATA_SOURCE="/path/to/my-bookmarks.js"
uv run flask run
```

### Multiple Configurations

Create a `.env` file:

```bash
BOOKMARKS_DATA_SOURCE=my-bookmarks.js
BOOKMARKS_DEBUG=true
BOOKMARKS_PORT=8080
```

Then run:

```bash
source .env
uv run flask run
```

### LLM Configuration

Configure the LLM provider and content extraction:

```bash
# Use Markdown extraction instead of HTML
export BOOKMARKS_LLM_CONTENT_FORMAT=markdown

# Use Perplexity MCP instead of direct API
export BOOKMARKS_LLM_PROVIDER=perplexity-mcp
export PERPLEXITY_API_KEY=pplx-your-key

# Or use a different provider (when available)
export BOOKMARKS_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key

uv run flask run
```

See [LLM Configuration Guide](docs/LLM_CONFIGURATION.md) for complete details on LLM configuration.

Note: The examples above use port `5001`, but the actual port used by the server can be changed with the `BOOKMARKS_PORT` environment variable or other runtime overrides (CLI args, service configs). If you start your server with `BOOKMARKS_PORT=5000`, use port `5000` in example URLs and shortcuts.

## Backup Behavior

On startup, the server automatically creates a timestamped backup of your bookmarks file in the `backup/` directory.

Backup files are named with the pattern: `{filename}_{timestamp}.{extension}.bck`

For example: `bookmarks_20241209_143052.js.bck`

### Backup Rotation

By default, the 5 most recent backups are kept. Older backups are automatically deleted when the limit is exceeded.

### Backup Configuration Examples

**Disable backups:**

```bash
export BOOKMARKS_BACKUP_ENABLED=false
```

**Change backup directory:**

```bash
export BOOKMARKS_BACKUP_DIR=/path/to/backups
```

**Keep more backups (e.g., 10):**

```bash
export BOOKMARKS_BACKUP_COUNT=10
```

**Disable rotation (keep all backups):**

```bash
export BOOKMARKS_BACKUP_COUNT=0
```
