# Bookmarks for Firefox

A toolbar button that saves the page you are reading to the bookmarks
server's capture API (`POST /api/items`). Manifest V3, Firefox only.

It sends the page's `url`, its `title`, the rendered `html` as the browser
holds it, and an optional `note` typed in the popup. The rendered page lets
the server keep pages it cannot fetch itself: Reddit, single-page apps,
logged-in pages. Pages scripts cannot reach (`about:` pages, the add-ons
site) are sent without html, and the server fetches them.

The popup shows the server's reply as the server words it: "Saved",
"Already saved on <date>", "…; note not added", "Re-queued". If the server
cannot be reached it shows "Not saved: server unreachable". Nothing is
retried later.

## Files

- `manifest.json`: permissions are `activeTab` and `scripting` (read the
  page you clicked on), `storage` (the server address) and an optional host
  permission for the server. Its `content_security_policy` drops Manifest
  V3's default `upgrade-insecure-requests`, which would rewrite every
  `http://` save to `https://` and fail against a plain-HTTP server
  ("server unreachable"; uvicorn logs "Invalid HTTP request"). (2026-10-07)
- `popup.html`, `popup.js`: the save popup.
- `options.html`, `options.js`: the server address.
- `server.js`: the stored address and its host permission, shared by both.
- `icons/`: toolbar and listing icons.

## Install

For a quick try, open `about:debugging#/runtime/this-firefox`, click
"Load Temporary Add-on…" and pick `manifest.json`. It is removed when
Firefox closes.

To keep it, sign it as an unlisted version of the existing add-on (the
gecko id is unchanged) with
[web-ext](https://extensionworkshop.com/documentation/develop/getting-started-with-web-ext/).
The API key and secret come from addons.mozilla.org's API key page; keep
them out of shell history and out of git.

```bash
npx web-ext sign --source-dir browser-extension --channel unlisted \
  --api-key "$AMO_JWT_ISSUER" --api-secret "$AMO_JWT_SECRET"
```

Then install the `.xpi` from `web-ext-artifacts/` via `about:addons` →
gear → "Install Add-on From File…".

## Configure

Open the extension's options (`about:addons` → Bookmarks → Options), enter
the server address, e.g. `http://thunderbird:5000`, and save. Firefox asks
once for permission to send data to that host; the address is saved only if
you allow it. The capture API needs no CORS settings.

## Manual test checklist

Run these against a local server (`uv run bookmarks serve`) with the
extension loaded temporarily. Watch the server's log for each request.

1. **No address.** On a fresh install, open the popup and click Save →
   "Not saved: set the server address in the extension options."
2. **Permission refused.** In options, enter the address and refuse
   Firefox's prompt → "Not saved: Firefox access to the server was
   refused."; the address is not stored.
3. **Configure.** Enter the address again and allow → "Saved." Reopen the
   options page: the address is shown.
4. **Saved, with html.** On an article page, type a note and click Save →
   green "Saved". `list_submissions` (MCP) shows the URL pending with the
   note; the server received `html` and `title`.
5. **Already saved.** Save the same page again with a note → yellow "Already
   saved on <date>; note not added".
6. **Tracking parameters.** Save the same page with `?utm_source=x` added →
   "Already saved on <date>".
7. **Logged-in or single-page app.** Save a Reddit thread or a page behind a
   login, then run `bookmarks drain` → the item's summary describes the page
   you saw, not a login wall.
8. **No html available.** Save `about:addons` or a page on
   addons.mozilla.org → "Not saved: not an http(s) URL…" for `about:`; for
   the add-ons site, "Saved" (sent without html).
9. **Re-queued.** Save a URL that fails (e.g. a 404 page), run
   `bookmarks drain` until `list_submissions` shows it failed, then save it
   again → yellow "Re-queued".
10. **Server down.** Stop the server and click Save → red, large
    "Not saved: server unreachable".
11. **Wrong address.** Set the address to a host that does not answer, e.g.
    `http://10.255.255.1:5000` → "Not saved: server unreachable" within
    about 15 seconds.
