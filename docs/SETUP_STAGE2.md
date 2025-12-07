# Stage 2 Setup Guide: LLM-Powered Bookmark Generation

This guide will help you set up automatic bookmark description generation using Perplexity AI.

## Prerequisites

- Perplexity Pro subscription ($20/month)
- Perplexity API key

## Step 1: Get Your Perplexity API Key

1. Go to [Perplexity API Settings](https://www.perplexity.ai/settings/api)
2. Click "Generate API Key"
3. Copy your API key (starts with `pplx-...`)
4. Keep it secure - you'll need it in the next step

## Step 2: Install Dependencies

```bash
# Install required Python packages with uv
uv add requests beautifulsoup4 lxml
```

## Step 3: Configure API Key

### Option A: Environment Variable (Recommended)

**Windows (PowerShell):**
```powershell
# Set for current session
$env:PERPLEXITY_API_KEY = "pplx-your-key-here"

# Set permanently (add to PowerShell profile)
[System.Environment]::SetEnvironmentVariable('PERPLEXITY_API_KEY', 'pplx-your-key-here', 'User')
```

**Windows (Command Prompt):**
```cmd
setx PERPLEXITY_API_KEY "pplx-your-key-here"
```

**Linux/Mac:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PERPLEXITY_API_KEY="pplx-your-key-here"

# Then reload
source ~/.bashrc
```

### Option B: .env File

Create a `.env` file in the project directory:

```bash
PERPLEXITY_API_KEY=pplx-your-key-here
```

## Step 4: Test the Setup

Create a test file with a few URLs:

```bash
# Create test_urls.txt
cat > test_urls.txt << EOF
https://github.com/python/cpython
https://news.ycombinator.com
https://www.perplexity.ai
EOF
```

Run a dry-run test:

```bash
uv run python tools/add_bookmarks_from_urls.py test_urls.txt --generate-descriptions --dry-run
```

Expected output:
```
✓ Initialized Perplexity client

[1/3] 🔍 Generating description for: https://github.com/python/cpython
         ✓ Title: Python Programming Language - Official Repository...
[2/3] 🔍 Generating description for: https://news.ycombinator.com
         ✓ Title: Hacker News - Technology and Startup Community...
[3/3] 🔍 Generating description for: https://www.perplexity.ai
         ✓ Title: Perplexity AI - Advanced Search Engine...

============================================================
Summary:
  Added: 3
  Skipped (duplicates): 0
  Total URLs processed: 3

LLM Usage Statistics:
  API Requests: 3
  Total Tokens: 450
  Estimated Cost: $0.0150
  (Your Pro subscription includes $5/month in credits)

(DRY RUN - no changes saved)
============================================================
```

## Step 5: Start Using It!

### Basic Usage

```bash
# Generate descriptions for URLs in a file
uv run python tools/add_bookmarks_from_urls.py my_urls.txt --generate-descriptions

# Preview without saving
uv run python tools/add_bookmarks_from_urls.py my_urls.txt --generate-descriptions --dry-run
```

### Without LLM (Stage 1)

```bash
# Add bookmarks with basic "unread" description
uv run python tools/add_bookmarks_from_urls.py my_urls.txt
```

## Usage Tips

### 1. Start Small
Process URLs in batches of 10-20 to monitor costs:

```bash
# Split large files
head -20 large_list.txt > batch1.txt
uv run python tools/add_bookmarks_from_urls.py batch1.txt --generate-descriptions
```

### 2. Monitor Your Usage

The script shows usage statistics after each run:
- **API Requests**: Number of Perplexity API calls
- **Total Tokens**: Tokens consumed
- **Estimated Cost**: Approximate cost in USD

With your Pro subscription's $5/month credits, you can process approximately:
- **1,000-2,500 URLs per month** (depending on content length)
- **33-83 URLs per day** if spread evenly

### 3. Handle Rate Limits

The script automatically:
- Adds 0.5s delay between requests
- Retries with exponential backoff on rate limit errors
- Falls back to basic entries if API fails

### 4. Cost Management

```bash
# Check estimated cost before committing
uv run python tools/add_bookmarks_from_urls.py urls.txt --generate-descriptions --dry-run

# Look for the "Estimated Cost" line in output
```

## Troubleshooting

### "Module not found: perplexity_client"

Make sure you're in the correct directory:
```bash
cd c:\Users\varigg\projects\python\bookmarks
```

### "Perplexity API key required"

Check that your API key is set:
```bash
# Windows PowerShell
echo $env:PERPLEXITY_API_KEY

# Linux/Mac
echo $PERPLEXITY_API_KEY
```

### "Rate limit exceeded"

The script handles this automatically, but if you see repeated errors:
- Wait a few minutes
- Process fewer URLs at once
- Check your API tier at perplexity.ai

### "Unable to fetch content"

Some URLs may be blocked or require authentication:
- The script will use fallback descriptions
- Check the URL is publicly accessible
- Some sites block automated requests

## Advanced Configuration

### Custom Rate Limiting

Edit `perplexity_client.py` to adjust delays:

```python
# In add_bookmarks function, change:
time.sleep(0.5)  # Increase to 1.0 or 2.0 for slower processing
```

### Change Model

Edit `perplexity_client.py`:

```python
self.model = "sonar-pro"  # Use more powerful model (higher cost)
```

Available models:
- `sonar` - Default, good balance (recommended)
- `sonar-pro` - More detailed, higher cost
- `sonar-reasoning` - Advanced reasoning

### Batch Processing Script

Create `process_batches.sh`:

```bash
#!/bin/bash
for file in batch*.txt; do
    echo "Processing $file..."
    uv run python tools/add_bookmarks_from_urls.py "$file" --generate-descriptions
    sleep 5  # Pause between batches
done
```

## Next Steps

1. ✅ Test with a few URLs
2. ✅ Verify descriptions are good quality
3. ✅ Monitor your API usage
4. ✅ Process your bookmark backlog in batches
5. ✅ Set up regular imports for new bookmarks

## Support

- Perplexity API Docs: https://docs.perplexity.ai
- Check API usage: https://www.perplexity.ai/settings/api
- Report issues: Create an issue in your project repo

---

**Enjoy automated bookmark management! 🎉**
