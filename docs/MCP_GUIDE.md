# MCP Integration Guide: Two Approaches

This guide explains the difference between using MCP in AI IDEs vs. in your own scripts, and how to set up both.

## Understanding MCP Architecture

### What is MCP?

Model Context Protocol (MCP) is a standardized way for AI applications to interact with external tools and data sources. Think of it as a "universal adapter" for AI assistants.

```
┌─────────────┐
│  AI Client  │  (Your script, Claude, Cursor, etc.)
└──────┬──────┘
       │ MCP Protocol (JSON-RPC)
       │
┌──────▼──────┐
│ MCP Server  │  (Perplexity, filesystem, database, etc.)
└──────┬──────┘
       │
┌──────▼──────┐
│   Service   │  (Perplexity API, files, DB, etc.)
└─────────────┘
```

## Approach 1: MCP in AI IDEs (Antigravity, Claude Desktop)

### How It Works

- **The AI assistant** uses MCP servers
- You configure servers in IDE settings
- The AI calls tools on your behalf
- You don't write code to use MCP

### Example: Antigravity Configuration

In your IDE settings, you might have:

```json
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-perplexity"],
      "env": {
        "PERPLEXITY_API_KEY": "pplx-xxx"
      }
    }
  }
}
```

Then when you ask me (Antigravity) to search the web, I can use the Perplexity MCP server automatically.

### Use Case

- Interactive AI assistance
- Ad-hoc queries
- Exploratory work
- No coding required

---

## Approach 2: MCP in Your Python Scripts

### How It Works

- **Your code** uses MCP servers
- You install MCP client library
- You programmatically call MCP tools
- Full control over the interaction

### Architecture

```python
Your Script (add_bookmarks_from_urls.py)
    ↓
MCP Client Library (mcp Python package)
    ↓ stdio (stdin/stdout)
MCP Server (npx @modelcontextprotocol/server-perplexity)
    ↓
Perplexity API
```

### Setup Steps

#### 1. Install Dependencies

```bash
# MCP Python SDK
uv add mcp

# Node.js (required to run npx)
# Download from: https://nodejs.org/
# Or use winget: winget install OpenJS.NodeJS
```

#### 2. Install Perplexity MCP Server

```bash
# This downloads the server when first run
npx -y @modelcontextprotocol/server-perplexity --help
```

#### 3. Set API Key

```powershell
$env:PERPLEXITY_API_KEY = "pplx-your-key-here"
```

#### 4. Use in Your Script

```python
from perplexity_mcp_client import PerplexityMCPClient

# Create MCP client
client = PerplexityMCPClient()

# Generate description (MCP handles everything)
result = client.generate_description("https://example.com")
print(result['title'])
print(result['description'])
```

### How It Works Internally

1. **Your script** calls `client.generate_description(url)`
2. **MCP client** spawns the MCP server as a subprocess:
   ```bash
   npx @modelcontextprotocol/server-perplexity
   ```
3. **Communication** happens via stdio (standard input/output):
   ```
   Your Script → stdin → MCP Server
   MCP Server → stdout → Your Script
   ```
4. **MCP server** calls Perplexity API
5. **Result** flows back through the chain

### Key Differences from Direct API

| Aspect          | Direct API                | MCP                        |
| --------------- | ------------------------- | -------------------------- |
| Setup           | Simple                    | Requires Node.js + MCP SDK |
| Control         | Full control              | Server abstracts details   |
| Web Scraping    | You do it (BeautifulSoup) | Server might do it         |
| Transport       | HTTP REST                 | stdio (JSON-RPC)           |
| Flexibility     | High                      | Medium                     |
| Standardization | API-specific              | Protocol-standard          |

---

## Comparison: Three Approaches

### 1. Direct API (Current Default Implementation)

**Implementation:** `bookmarks/services/llm_providers.py` (PerplexityProvider class)

```python
# You control everything
response = requests.get(url)  # Fetch page
soup = BeautifulSoup(response.text)  # Parse
text = soup.get_text()  # Extract

# Call Perplexity API directly
result = requests.post('https://api.perplexity.ai/chat/completions', ...)
```

**Usage:**

```python
from bookmarks.services import LLMFactory
service = LLMFactory.create_client(provider="perplexity", content_format="html")
```

**Pros:**

- ✅ Simple setup
- ✅ Full control
- ✅ No extra dependencies
- ✅ Easy to debug

**Cons:**

- ❌ You handle web scraping
- ❌ Not standardized
- ❌ API-specific code

### 2. MCP in Your Script (New Option)

**File:** `perplexity_mcp_client.py`

```python
# MCP handles the details
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        result = await session.call_tool("perplexity_ask", {"query": url})
```

**Pros:**

- ✅ Standardized protocol
- ✅ Server handles complexity
- ✅ Can switch providers easily
- ✅ Future-proof

**Cons:**

- ❌ Requires Node.js
- ❌ More complex setup
- ❌ Async code (more complex)
- ❌ Less control

### 3. MCP in AI IDE (Antigravity)

**Configuration only, no code**

**Pros:**

- ✅ No coding needed
- ✅ AI uses it automatically
- ✅ Interactive

**Cons:**

- ❌ Not for automation
- ❌ Can't use in scripts
- ❌ Requires AI IDE

---

## When to Use Each Approach

### Use Direct API When:

- ✅ You want simple, straightforward code
- ✅ You need full control over web scraping
- ✅ You're building a standalone script
- ✅ You want to minimize dependencies

### Use MCP in Scripts When:

- ✅ You want to experiment with MCP
- ✅ You might switch between providers
- ✅ You want standardized tool calling
- ✅ You're building a larger system

### Use MCP in IDE When:

- ✅ You want AI assistance
- ✅ You're doing interactive work
- ✅ You don't need automation

---

## Trying MCP in Your Bookmark Script

### Option A: Add MCP Support (Keep Both)

Update `add_bookmarks_from_urls.py`:

```python
parser.add_argument(
    "--use-mcp",
    action="store_true",
    help="Use MCP protocol instead of direct API"
)

# In the code:
from bookmarks.services import LLMFactory

service = LLMFactory.create_client(
    provider="perplexity",
    use_mcp=args.use_mcp  # True for MCP, False for direct API
)
```

Usage:

```bash
# Direct API (default)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# MCP protocol
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --use-mcp
```

> **Note:** The `--use-mcp` flag is already implemented in the tools. See [LLM Configuration Guide](LLM_CONFIGURATION.md) for more details.

---

## MCP Server Communication

### Stdio Transport (What We Use)

```
┌──────────────┐
│ Your Script  │
└──────┬───────┘
       │ spawn subprocess
       ▼
┌──────────────┐
│  npx server  │
└──────┬───────┘
       │
   stdin/stdout (JSON-RPC messages)
       │
┌──────▼───────┐
│ Your Script  │
└──────────────┘
```

Messages look like:

```json
// Your script → Server
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "perplexity_ask",
    "arguments": {"query": "..."}
  }
}

// Server → Your script
{
  "jsonrpc": "2.0",
  "result": {
    "content": "..."
  }
}
```

### HTTP Transport (Alternative)

Some MCP servers can run as HTTP services:

```bash
# Start server
mcp-server-perplexity --port 3000

# Your script connects via HTTP
response = requests.post('http://localhost:3000/mcp', ...)
```

**Note:** Most MCP servers use stdio by default.

---

## Next Steps

### To Experiment with MCP:

1. **Install Node.js**

   ```bash
   winget install OpenJS.NodeJS
   ```

2. **Install MCP SDK**

   ```bash
   uv add mcp
   ```

3. **Test the MCP client**

   ```python
   from perplexity_mcp_client import PerplexityMCPClient

   client = PerplexityMCPClient()
   result = client.generate_description("https://github.com/python/cpython")
   print(result)
   ```

4. **Compare with direct API**
   - Try both approaches
   - Compare speed, reliability, results
   - Choose what works best for you

### Resources

- MCP Specification: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Perplexity MCP Server: https://github.com/modelcontextprotocol/servers

---

## Summary

**MCP in AI IDEs (Antigravity):**

- Configuration-based
- AI uses it for you
- No coding needed

**MCP in Your Scripts:**

- Code-based
- You control it
- Standardized protocol
- Requires setup

**Direct API (Current):**

- Simplest approach
- Full control
- No MCP needed

Choose based on your needs! For your bookmark script, **direct API is simpler**, but **MCP is great for learning** and future flexibility.
