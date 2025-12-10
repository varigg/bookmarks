# Firefox Browser Extension for Bookmarks Server

This extension adds a toolbar button to Firefox that allows you to quickly save the current page to your self-hosted bookmarks server.

## Features

- 🔖 One-click bookmark addition from any webpage
- 📝 Edit title, description, and tags before saving
- ⚙️ Configurable server URL for self-hosting
- 🚀 Fast and lightweight

## Installation

### Step 1: Generate Icon Files

Before installing, you need to create PNG icons from the SVG file:

1. Navigate to `browser-extension/icons/`
2. Follow the instructions in `icons/README.md` to convert `bookmark.svg` to PNG files
3. You need: `bookmark-16.png`, `bookmark-32.png`, `bookmark-48.png`, `bookmark-96.png`

### Step 2: Install in Firefox

#### Temporary Installation (for testing)

1. Open Firefox
2. Navigate to `about:debugging#/runtime/this-firefox`
3. Click "Load Temporary Add-on..."
4. Select the `manifest.json` file from the `browser-extension/` directory
5. The extension is now installed (will be removed when you close Firefox)

#### Permanent Installation (unsigned)

Firefox requires extensions to be signed for permanent installation. You have two options:

**Option A: Use Firefox Developer Edition or Nightly**

1. Install [Firefox Developer Edition](https://www.mozilla.org/en-US/firefox/developer/) or [Firefox Nightly](https://www.mozilla.org/en-US/firefox/channel/desktop/)
2. Navigate to `about:config`
3. Set `xpinstall.signatures.required` to `false`
4. Create a ZIP file of the extension:
   ```bash
   cd browser-extension
   zip -r bookmarks-extension.zip manifest.json popup.html popup.js options.html options.js icons/
   ```
5. Navigate to `about:addons`
6. Click the gear icon → "Install Add-on From File..."
7. Select `bookmarks-extension.zip`

**Option B: Sign the extension (recommended for production)**

1. Create an account at [addons.mozilla.org](https://addons.mozilla.org/developers/)
2. Get API credentials
3. Use [web-ext](https://extensionworkshop.com/documentation/develop/getting-started-with-web-ext/) to sign:
   ```bash
   npm install -g web-ext
   cd browser-extension
   web-ext sign --api-key=YOUR_API_KEY --api-secret=YOUR_API_SECRET
   ```
4. Install the signed `.xpi` file

### Step 3: Configure the Extension

1. Click the extension icon in the toolbar
2. Click "Configure Server URL" at the bottom
3. Enter your bookmarks server URL (default: `http://localhost:5001`)
4. Click "Save Settings"

## Usage

1. Navigate to any webpage you want to bookmark
2. Click the bookmark extension icon in the toolbar
3. The URL and title are automatically filled in
4. Optionally edit the title, add a description, or add tags
5. Click "Add Bookmark"
6. The bookmark is sent to your server!

## Server Requirements

Your bookmarks server must:

- Be running and accessible at the configured URL
- Accept POST requests to `/bookmarks` endpoint
- Accept form data with fields: `url`, `title`, `description`, `tags`

This extension works with the bookmarks server in this repository.

## Troubleshooting

### "Failed to connect to server"

- Ensure your bookmarks server is running
- Check the server URL in the extension settings
- If using HTTPS, ensure your certificate is valid
- Check browser console for CORS errors

### CORS Issues

If your server is on a different domain, you may need to add CORS headers to your Flask app:

```python
from flask_cors import CORS
CORS(app)
```

### Icons not showing

- Make sure you generated the PNG icon files from the SVG
- See `icons/README.md` for instructions

## Development

To modify the extension:

1. Edit the files in `browser-extension/`
2. Reload the extension in `about:debugging`
3. Test your changes

## Files

- `manifest.json` - Extension metadata and permissions
- `popup.html` - The popup UI shown when clicking the icon
- `popup.js` - Logic for the popup form
- `options.html` - Settings page
- `options.js` - Settings logic
- `icons/` - Extension icons
