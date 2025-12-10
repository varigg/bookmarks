# MarkItDown vs BeautifulSoup for Content Extraction

> **For complete configuration details, see [LLM Configuration Guide](LLM_CONFIGURATION.md)**

## Overview

Comparison of three approaches for extracting web page content before sending to LLM.

## Approaches

### 1. BeautifulSoup (Current Default)

**Implementation:** `bookmarks/services/content_extractor.py` (HTMLExtractor class)

**How it works:**

```python
soup = BeautifulSoup(response.text, 'html.parser')
for script in soup(['script', 'style', 'nav', 'footer', 'header']):
    script.decompose()
text = soup.get_text()  # Plain text only
```

**Output example:**

```
Python Programming Language
The official home of the Python Programming Language
Download Documentation Community Success Stories News Events
Python is a programming language that lets you work quickly...
```

**Pros:**

- ✅ Simple and lightweight
- ✅ Fast extraction
- ✅ No extra dependencies
- ✅ Small token count

**Cons:**

- ❌ Loses all structure
- ❌ No semantic information
- ❌ Links are lost
- ❌ Hard to identify main topics
- ❌ Navigation text mixed with content

**Best for:**

- Simple pages
- When minimizing tokens is critical
- When speed is priority

---

### 2. MarkItDown (New Option)

**File:** `perplexity_client_markdown.py`

**How it works:**

```python
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert_stream(response.content)
markdown_text = result.text_content
```

**Output example:**

```markdown
# Python Programming Language

The official home of the Python Programming Language

## Features

Python is a programming language that lets you work quickly...

- **Easy to learn**: Simple syntax
- **Powerful**: Rich standard library
- **Versatile**: [Web](https://www.python.org/web), data science, automation

[Download](https://www.python.org/downloads/) | [Documentation](https://docs.python.org)
```

**Pros:**

- ✅ **Preserves structure** (headings, lists, emphasis)
- ✅ **Better LLM understanding** (knows what's important)
- ✅ **Keeps links** (with context)
- ✅ **Semantic meaning** (bold = important)
- ✅ **Better titles** (extracts H1)
- ✅ **More accurate summaries**
- ✅ **Handles tables** properly

**Cons:**

- ❌ Additional dependency (`markitdown`)
- ❌ Slightly slower
- ❌ ~20-30% more tokens
- ❌ May need token limit adjustments

**Best for:**

- Complex pages with structure
- Documentation sites
- Articles with sections
- When quality > token cost

---

### 3. MCP Protocol

**File:** `perplexity_mcp_client.py`

**How it works:**

```python
# MCP server handles content fetching
result = await session.call_tool(
    "perplexity_ask",
    arguments={"messages": messages}
)
```

**Pros:**

- ✅ Standardized protocol
- ✅ Server handles complexity
- ✅ Future-proof

**Cons:**

- ❌ Requires Node.js + MCP server
- ❌ More complex setup
- ❌ Less control over extraction

**Best for:**

- Learning MCP
- Standardized workflows
- When switching providers

---

## Comparison Table

| Feature          | BeautifulSoup    | MarkItDown   | MCP             |
| ---------------- | ---------------- | ------------ | --------------- |
| **Setup**        | Simple           | Simple       | Complex         |
| **Dependencies** | `beautifulsoup4` | `markitdown` | `mcp` + Node.js |
| **Speed**        | Fast             | Medium       | Medium          |
| **Token Usage**  | Low              | Medium       | Varies          |
| **Structure**    | ❌ Lost          | ✅ Preserved | Varies          |
| **Links**        | ❌ Lost          | ✅ Preserved | Varies          |
| **Headings**     | ❌ Lost          | ✅ Preserved | Varies          |
| **Tables**       | ❌ Broken        | ✅ Formatted | Varies          |
| **LLM Quality**  | Good             | **Better**   | Good            |
| **Control**      | Full             | Full         | Limited         |

## Real-World Example

### Input URL

`https://github.com/python/cpython`

### BeautifulSoup Output (Plain Text)

```
GitHub python cpython The Python programming language Notifications Fork 18.5k
Star 64.2k Code Issues Pull requests Actions Projects Security Insights
python cpython Public Notifications Fork 18.5k Star 64.2k The Python
programming language python.org License View license 64.2k stars 18.5k
forks Branches Tags Activity Star Notifications Code Issues Pull requests
Actions Projects Security Insights More Code Folders and files Name Last
commit message Last commit date Latest commit History 19,766 Commits...
```

**LLM sees:** Wall of text, hard to identify what's important

### MarkItDown Output (Markdown)

```markdown
# python/cpython

The Python programming language

⭐ 64.2k | 🍴 18.5k | [python.org](https://python.org)

## About

CPython is the reference implementation of the Python programming language.
Written in C and Python, CPython is the default and most widely-used
implementation of the Python language.

## Repository Structure

- **Doc/** - Documentation source files
- **Grammar/** - Grammar definition
- **Include/** - C header files
- **Lib/** - Standard library modules
- **Modules/** - C extension modules

[View on GitHub](https://github.com/python/cpython)
```

**LLM sees:** Clear structure, knows it's a GitHub repo, understands the purpose

### Result Quality

**BeautifulSoup Title:**

> "GitHub - python/cpython repository page"

**MarkItDown Title:**

> "CPython - Python Programming Language Reference Implementation"

**BeautifulSoup Description:**

> "GitHub repository for Python programming language with code, issues, and pull requests."

**MarkItDown Description:**

> "CPython is the reference implementation of the Python programming language, written in C and Python. This repository contains the source code, documentation, standard library, and C extension modules that form the foundation of the most widely-used Python implementation."

## Recommendation

### Use MarkItDown When:

- ✅ Quality is more important than cost
- ✅ Processing documentation or articles
- ✅ Pages have clear structure (headings, lists)
- ✅ You want better, more accurate descriptions
- ✅ Token cost is acceptable (~20-30% increase)

### Use BeautifulSoup When:

- ✅ Processing many URLs (cost matters)
- ✅ Simple pages without much structure
- ✅ Speed is critical
- ✅ Token limits are tight

### Use MCP When:

- ✅ Learning the protocol
- ✅ Building standardized workflows
- ✅ May switch providers later

## Implementation

### Install MarkItDown

```bash
uv add markitdown
```

### Use with LLMFactory

```python
from bookmarks.services import LLMFactory

# HTML extraction (default)
service = LLMFactory.create_client(provider="perplexity", content_format="html")

# Markdown extraction
service = LLMFactory.create_client(provider="perplexity", content_format="markdown")

# MCP protocol
service = LLMFactory.create_client(provider="perplexity", use_mcp=True)
```

### CLI Usage

```bash
# Use HTML extraction (default)
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions

# Use Markdown extraction
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --use-markdown

# Use MCP protocol
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --use-mcp
```

> **See [LLM Configuration Guide](LLM_CONFIGURATION.md) for complete configuration details.**

# Use MCP

uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --use-mcp

```

## Conclusion

**MarkItDown is worth it** for most use cases. The improved quality of titles and descriptions outweighs the small increase in token usage. The LLM can better understand page structure and generate more accurate, informative bookmark entries.

**Recommendation:** Make MarkItDown the **default** and keep BeautifulSoup as a fallback for edge cases or cost-sensitive scenarios.
```
