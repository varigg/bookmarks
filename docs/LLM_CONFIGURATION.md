# LLM Service Configuration Guide

The bookmark application uses a flexible, composition-based LLM architecture that supports multiple providers and content extraction strategies.

## Architecture Overview

The LLM service is built on three composable layers:

1. **LLM Providers** - Handle API calls to specific LLM services (Perplexity, OpenAI, Anthropic)
2. **Content Extractors** - Extract content from web pages (HTML or Markdown format)
3. **LLM Service** - Orchestrates content extraction, prompt building, retries, and response parsing

## Quick Start

### Basic Setup (Perplexity API)

```bash
# 1. Install dependencies
uv add requests beautifulsoup4 lxml

# 2. Set your API key
export PERPLEXITY_API_KEY="pplx-your-key-here"

# 3. Run the application
uv run flask --app wsgi run
```

The application will automatically use Perplexity with HTML content extraction (default).

## Configuration Options

### Provider Selection

Currently supported providers:

- **perplexity** (default) - Perplexity API with direct HTTP calls
- **perplexity-mcp** - Perplexity via Model Context Protocol
- **openai** - Coming soon
- **anthropic** - Coming soon

### Content Extraction Strategies

Choose how web pages are processed before sending to the LLM:

#### HTML Extraction (Default)

- Uses BeautifulSoup to extract clean text
- Removes scripts, styles, navigation elements
- Fast and lightweight
- Best for: Most use cases

```python
from bookmarks.services import LLMFactory

service = LLMFactory.create_client(
    provider="perplexity",
    content_format="html"
)
```

#### Markdown Extraction

- Uses MarkItDown to convert pages to markdown
- Preserves document structure and formatting
- Better semantic understanding
- Best for: Technical documentation, articles with structure

```bash
# Install MarkItDown
uv add markitdown

# Use in code
```

```python
from bookmarks.services import LLMFactory

service = LLMFactory.create_client(
    provider="perplexity",
    content_format="markdown"
)
```

#### MCP Protocol

- Uses Model Context Protocol
- Server fetches content itself (no extractor needed)
- Best for: Advanced integrations, distributed systems

**Setup:**

```bash
# 1. Install MCP Python package
uv add mcp

# 2. Install Perplexity MCP server (requires Node.js)
npm install -g @perplexity-ai/mcp-server

# 3. Configure to use perplexity-mcp provider
export BOOKMARKS_LLM_PROVIDER=perplexity-mcp
export PERPLEXITY_API_KEY=pplx-your-key

# 4. Start the application
uv run flask --app wsgi run
```

**In Python code:**

```python
from bookmarks.services import LLMFactory

# Use perplexity-mcp provider
service = LLMFactory.create_client(provider="perplexity-mcp")
```

## Using the LLM Service

### From Python Code

```python
from bookmarks.services import LLMFactory

# Create service with your preferred configuration
service = LLMFactory.create_client(
    provider="perplexity",        # Provider: perplexity, openai, anthropic
    content_format="html",        # Extractor: html, markdown
    use_mcp=False,                # Use MCP protocol?
    api_key="pplx-your-key"       # Optional (uses env var if not provided)
)

# Generate description for a URL
result = service.generate_description("https://example.com")
print(result["title"])
print(result["description"])

# Check usage statistics
stats = service.get_usage_stats()
print(f"Requests: {stats['requests']}")
print(f"Cost: ${stats['estimated_cost_usd']:.2f}")
```

### From Command Line Tools

The `add_bookmarks_from_urls.py` tool supports all configuration options:

```bash
# Test your configuration first
uv run python tools/add_bookmarks_from_urls.py --test
uv run python tools/add_bookmarks_from_urls.py --test --provider perplexity-mcp
uv run python tools/add_bookmarks_from_urls.py --test --content-format markdown

# Default: Perplexity + HTML
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Use Markdown extraction
uv run python tools/add_bookmarks_from_urls.py urls.txt \
    --generate-descriptions --content-format markdown

# Use Perplexity MCP
uv run python tools/add_bookmarks_from_urls.py urls.txt \
    --generate-descriptions --provider perplexity-mcp

# Combine options
uv run python tools/add_bookmarks_from_urls.py urls.txt \
    --generate-descriptions --provider perplexity --content-format markdown
```

### From Web Interface

The web interface uses configuration from environment variables. Set these to change the default provider and content format:

```bash
# Use Markdown extraction instead of HTML
export BOOKMARKS_LLM_CONTENT_FORMAT=markdown

# Use OpenAI instead of Perplexity (when available)
export BOOKMARKS_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key
```

Restart the Flask application after changing environment variables.

## Environment Variables

### API Keys

| Variable             | Default | Description                        |
| -------------------- | ------- | ---------------------------------- |
| `PERPLEXITY_API_KEY` | None    | Your Perplexity API key (required) |
| `OPENAI_API_KEY`     | None    | OpenAI API key (when available)    |
| `ANTHROPIC_API_KEY`  | None    | Anthropic API key (when available) |

### LLM Configuration

| Variable                       | Default      | Description                                              |
| ------------------------------ | ------------ | -------------------------------------------------------- |
| `BOOKMARKS_LLM_PROVIDER`       | `perplexity` | LLM provider (`perplexity`, `openai`, `anthropic`)       |
| `BOOKMARKS_LLM_CONTENT_FORMAT` | `html`       | Content extraction format (`html`, `markdown`)           |
| `BOOKMARKS_LLM_USE_MCP`        | `false`      | Use MCP protocol instead of direct API (`true`, `false`) |

### Configuration Examples

**Use Markdown extraction by default:**

```bash
export BOOKMARKS_LLM_CONTENT_FORMAT=markdown
uv run flask --app wsgi run
```

**Switch to a different provider (when available):**

```bash
export BOOKMARKS_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key-here
uv run flask --app wsgi run
```

**Combine custom settings:**

```bash
# Use Anthropic with Markdown extraction
export BOOKMARKS_LLM_PROVIDER=anthropic
export BOOKMARKS_LLM_CONTENT_FORMAT=markdown
export ANTHROPIC_API_KEY=sk-ant-your-key
uv run flask --app wsgi run
```

**Use Perplexity MCP Server:**

```bash
# Set provider to perplexity-mcp (requires @perplexity-ai/mcp-server installed)
export BOOKMARKS_LLM_PROVIDER=perplexity-mcp
export PERPLEXITY_API_KEY=pplx-your-key
uv run flask --app wsgi run
```

> **Note:** These environment variables affect the web interface and any code using `BookmarkService.generate_metadata()`. Command-line tools like `add_bookmarks_from_urls.py` use the `--provider` and `--content-format` flags which work the same way as the environment variables.

## Advanced Configuration

### Custom Provider Implementation

To add a new LLM provider, implement the `LLMProvider` protocol:

```python
from bookmarks.services.llm_providers import LLMProvider
from typing import Dict, Any

class CustomProvider:
    """Custom LLM provider implementation."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Your initialization code

    def call_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Make API call to your LLM provider.

        Returns:
            Dict with 'content' (response text) and 'usage' (token stats) keys
        """
        # Your API call logic here
        return {
            "content": "LLM response text",
            "usage": {"total_tokens": 150}
        }
```

Then use it with LLMService:

```python
from bookmarks.services import LLMService, HTMLExtractor

provider = CustomProvider(api_key="your-key")
service = LLMService(
    provider=provider,
    content_extractor=HTMLExtractor()
)
```

### Custom Content Extractor

Implement the `ContentExtractor` protocol:

```python
from bookmarks.services.content_extractor import ContentExtractor
from typing import Dict

class CustomExtractor:
    """Custom content extraction implementation."""

    def extract(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Extract content from a URL.

        Returns:
            Dict with extracted content (keys vary by implementation)
        """
        # Your extraction logic here
        return {
            "title": "Page Title",
            "text": "Page content...",
            "meta_description": "Page description"
        }
```

## Comparison: HTML vs Markdown vs MCP

| Feature             | HTML          | Markdown      | MCP          |
| ------------------- | ------------- | ------------- | ------------ |
| Speed               | ⚡ Fast       | ⚡ Fast       | 🐢 Slower    |
| Setup Complexity    | ✅ Simple     | ✅ Simple     | ⚠️ Complex   |
| Dependencies        | Minimal       | +markitdown   | +mcp, +npx   |
| Content Quality     | Good          | Better        | Good         |
| Structure Preserved | ❌ No         | ✅ Yes        | Varies       |
| Best For            | General use   | Documentation | Advanced use |
| Network Calls       | 1 (fetch URL) | 1 (fetch URL) | Server-side  |

## Cost Estimation

Based on Perplexity Sonar model (estimates may vary):

| Usage       | Estimated Cost |
| ----------- | -------------- |
| 100 URLs    | ~$0.50         |
| 500 URLs    | ~$2.50         |
| 1,000 URLs  | ~$5.00         |
| 10,000 URLs | ~$50.00        |

**Tip:** Use `--dry-run` flag to preview without making API calls.

## Troubleshooting

### "API key required" Error

```bash
# Check if API key is set
echo $PERPLEXITY_API_KEY

# If not set, export it
export PERPLEXITY_API_KEY="pplx-your-key-here"
```

### "Module not found" Errors

```bash
# For HTML extraction (default)
uv add requests beautifulsoup4 lxml

# For Markdown extraction
uv add markitdown

# For MCP protocol
uv add mcp
npm install -g @perplexity-ai/mcp-server
```

### Rate Limiting (429 Errors)

The LLM service automatically handles rate limiting with exponential backoff. You'll see:

```
  Rate limited, waiting 2s...
  Rate limited, waiting 4s...
  Rate limited, waiting 8s...
```

This is normal and the service will retry automatically.

### High Costs

1. **Use dry-run first**: Preview what will be processed

   ```bash
   uv run python tools/add_bookmarks_from_urls.py urls.txt --dry-run
   ```

2. **Process in batches**: Split large lists into smaller chunks

   ```bash
   head -100 urls.txt > batch1.txt
   uv run python tools/add_bookmarks_from_urls.py batch1.txt --generate-descriptions
   ```

3. **Monitor usage**: Check statistics regularly
   ```python
   stats = service.get_usage_stats()
   print(f"Total cost this month: ${stats['estimated_cost_usd']:.2f}")
   ```

## Best Practices

1. **Start with HTML extraction** - It works well for most use cases
2. **Use Markdown for technical content** - Better for documentation and structured articles
3. **Test with --dry-run first** - Avoid unexpected API costs
4. **Monitor usage regularly** - Keep track of API costs
5. **Use MCP for advanced cases** - Only when you need distributed processing

## Future Providers

Support for additional providers is planned:

- **OpenAI (GPT-4)** - General purpose, strong reasoning
- **Anthropic (Claude)** - Long context, detailed analysis
- **Google (Gemini)** - Multimodal capabilities

Check the [Future Enhancements](dev/FUTURE_ENHANCEMENTS.md) document for updates.
