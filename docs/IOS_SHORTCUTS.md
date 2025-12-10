# iOS Shortcuts Integration Guide

Add bookmarks from Safari or any iOS app using the Share Sheet and Shortcuts app.

## Overview

This integration allows you to:

- Share any URL from Safari, Chrome, or other apps directly to your bookmarks server
- Use iOS Shortcuts app to send the URL to your server's API
- Add bookmarks with one tap from the Share Sheet

## Prerequisites

- iOS 13 or later
- Shortcuts app (pre-installed on iOS)
- Your bookmarks server accessible from your iOS device
- Server URL (e.g., `http://192.168.1.100:5001` or `https://bookmarks.yourdomain.com`)

## Setup Instructions

### Step 1: Find Your Server URL

Your bookmarks server needs to be accessible from your iOS device:

**Option A: Local Network**

- Find your computer's local IP address:
  ```bash
  hostname -I | awk '{print $1}'
  ```
- Your server URL will be: `http://YOUR_IP:5001`
- Example: `http://192.168.1.100:5001`

**Option B: Public Server**

- If you've deployed your server publicly: `https://bookmarks.yourdomain.com`

**Note:** For local network access, ensure:

1. Your iOS device is on the same WiFi network
2. Your firewall allows connections on port 5001
3. The server is running with `--host=0.0.0.0`:
   ```bash
   uv run flask --app wsgi run --host=0.0.0.0 --port=5001
   ```

### Step 2: Create the Shortcut

1. **Open Shortcuts app** on your iPhone/iPad

2. **Create a new shortcut:**

   - Tap the **"+"** button in the top right
   - Tap **"Add Action"**

3. **Add the following actions in order:**

   **Action 1: Get URLs from Input**

   - Search for "Get URLs from Input"
   - Add this action
   - This extracts the URL being shared

   **Action 2: Get Contents of URL** (API Request)

   - Search for "Get Contents of URL"
   - Add this action
   - Configure it:
     - **URL:** `http://YOUR_SERVER_IP:5001/api/bookmarks`
       - Replace `YOUR_SERVER_IP` with your actual server address
     - **Method:** `POST`
     - **Request Body:** `JSON`
     - Tap "Add new field" and add:
       - Key: `url`
       - Value: Tap and select **"URLs"** from the previous step

   **Action 3: Show Result** (Optional - for confirmation)

   - Search for "Show Result"
   - Add this action
   - Tap on the placeholder and select **"Contents of URL"**
   - This shows a success message

4. **Configure shortcut details:**
   - Tap the shortcut name at the top
   - Rename it to "Add to Bookmarks" (or any name you prefer)
   - Toggle **"Show in Share Sheet"** to ON
   - Under "Share Sheet Types", ensure **URLs** and **Safari web pages** are enabled
   - Tap "Done"

### Step 3: Use the Shortcut

1. **From Safari or any app:**

   - Navigate to a page you want to bookmark
   - Tap the **Share** button (square with arrow)
   - Scroll down and find **"Add to Bookmarks"** (or your shortcut name)
   - Tap it

2. **The shortcut will:**

   - Extract the URL
   - Send it to your server
   - Generate title and description using LLM
   - Save the bookmark
   - Show a confirmation message

3. **Check your bookmarks:**
   - Open your bookmarks web interface
   - The new bookmark should appear with auto-generated title and description

## Advanced Configuration

### Add Tags Automatically

To add default tags to bookmarks from iOS:

1. Edit your shortcut
2. In the "Get Contents of URL" action:
3. Tap "Add new field" and add:
   - Key: `tags`
   - Value: `["mobile", "unread"]` (customize as needed)

### Error Handling

Add error handling to show when something goes wrong:

1. After "Get Contents of URL" action, add:
2. Search for "Get Dictionary from Input"
3. Add "Get Value for Key" action:
   - Key: `success`
4. Add "If" action:
   - Condition: `success` equals `true`
5. In the "If" block, add "Show Notification":
   - Text: "Bookmark added successfully!"
6. In the "Otherwise" block, add "Show Alert":
   - Text: "Failed to add bookmark"

### Widget Support

You can also:

- Add the shortcut to your home screen as a widget
- Use Siri: "Hey Siri, run Add to Bookmarks" (then paste the URL)

## Troubleshooting

### "Could not connect to server"

**Problem:** Shortcut can't reach your server

**Solutions:**

1. Verify server is running: `curl http://YOUR_IP:5001/api/bookmarks`
2. Check both devices are on same WiFi network
3. Disable any VPNs temporarily
4. Try the server's IP address instead of hostname
5. Ensure firewall allows port 5001

### "Invalid response"

**Problem:** Server returned an error

**Solutions:**

1. Check server logs for errors
2. Verify the API endpoint is `/api/bookmarks`
3. Ensure CORS is enabled (already configured if you installed the browser extension)
4. Test with curl:
   ```bash
   curl -X POST http://YOUR_IP:5001/api/bookmarks \
     -H "Content-Type: application/json" \
     -d '{"url":"https://example.com"}'
   ```

### Shortcut doesn't appear in Share Sheet

**Solutions:**

1. Edit the shortcut
2. Ensure "Show in Share Sheet" is toggled ON
3. Check "Share Sheet Types" includes URLs and Safari web pages
4. Restart Shortcuts app

## Server Configuration for iOS

When running the server for iOS access:

```bash
# Allow connections from network
uv run flask --app wsgi run --host=0.0.0.0 --port=5001
```

Or set in your environment:

```bash
export BOOKMARKS_PORT=5001
uv run flask --app wsgi run --host=0.0.0.0
```

## Security Considerations

### Local Network Only

- Keep server on local network only (safest)
- No authentication needed if only accessible locally

### Public Server

If exposing publicly:

1. Use HTTPS (required for iOS to trust connection)
2. Consider adding API key authentication
3. Use environment variable for API key
4. Add rate limiting

Example with API key (future enhancement):

```python
@bp.before_request
def check_api_key():
    if request.endpoint == 'main.api_create_bookmark':
        api_key = request.headers.get('X-API-Key')
        if api_key != config.API_KEY:
            return {"error": "Unauthorized"}, 401
```

Then in iOS Shortcut, add header:

- Key: `X-API-Key`
- Value: `your-secret-key`

## Alternative: Using Siri

You can invoke the shortcut with Siri:

1. Copy the URL you want to bookmark
2. Say: "Hey Siri, Add to Bookmarks"
3. Siri will run the shortcut with the copied URL

## Example Shortcut Flow

```
┌─────────────────────────┐
│  Share URL from Safari  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Get URLs from Input    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  POST to /api/bookmarks             │
│  Body: {"url": "https://..."}       │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  Show Success Message   │
└─────────────────────────┘
```

## Next Steps

- Test the shortcut with various websites
- Customize the confirmation message
- Add more tags or metadata as needed
- Create additional shortcuts for specific use cases (e.g., "Save Recipe", "Save Article")
