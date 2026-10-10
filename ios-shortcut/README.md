# Bookmarks for iPhone

Two Shortcuts that save a link from the share sheet to the bookmarks
server's capture API (`POST /api/items`). They are built by hand in the
Shortcuts app; iOS will not import an unsigned shortcut file, so this
document is the deliverable.

| Shortcut | Appears for | Sends |
|---|---|---|
| **Save page** | Safari web pages | `url`, `title`, the rendered `html`, `note` |
| **Save link** | links shared from any other app | `url`, `note` |

Why two: the page's rendered HTML comes from Shortcuts' "Run JavaScript on
Web Page" action, which only works on a Safari web page and fails on a plain
link. iOS picks the Shortcut by what is being shared, so nothing has to
branch. In Safari's share sheet both are listed; choose **Save page**.

The rendered page lets the server keep pages it cannot fetch itself (Reddit,
single-page apps, logged-in pages), the same as the Firefox extension.

> The action names below are from iOS 17/18 and written without a phone in
> front of the author. If an action is called something else on your
> version, the **manual test checklist** at the end is the check; correct
> this document as you find differences.

## What the server needs

The capture API treats an empty `html`, `title` or `note` as absent, so
**Save link** can send empty strings and every field can always be present.
A reply to a good request has a `message` ("Saved", "Already saved on
<date>", "…; note not added", "Re-queued"). A rejected request (for example
a URL that is not http or https) replies with a `detail` instead and no
`message`. Both Shortcuts show whichever one arrives.

## Server address

The phone must be able to reach the server. Use an address your phone
resolves, such as the server's LAN IP or its Tailscale name:
`http://<address>:5000`. Names that only the Windows/Samba network knows
(NetBIOS, e.g. a bare `thunderbird`) do not resolve on iOS. Away from home
the server is reachable only over Tailscale or a VPN to your network. The
address is typed once, in the first action of each Shortcut.

## Build: Save page

New Shortcut named **Save page**. In its details (ⓘ), turn on **Show in
Share Sheet** and set **Share Sheet Types** to **Safari web pages** only.

1. **Text** → `http://<address>:5000`.
2. **Run JavaScript on Web Page** (input: Shortcut Input) with:
   ```js
   completion(document.documentElement.outerHTML);
   ```
3. **Get Details of Safari Web Page** (Shortcut Input) → **Page URL**.
4. **Get Details of Safari Web Page** (Shortcut Input) → **Name** (the title).
5. **Ask for Input** (Text), prompt "Note (optional)". Leave it empty and
   tap Done to skip. **Cancel stops the whole Shortcut and saves nothing.**
6. **Get Contents of URL**:
   - URL: the Text from step 1 followed by `/api/items`
   - Method: **POST**; Request Body: **JSON**
   - Fields (all Text): `url` = the Page URL, `title` = the Name,
     `html` = the JavaScript result, `note` = the Provided Input.
7. **Get Dictionary Value** for `message` from the Contents of URL.
8. **If** that value **has any value**: **Show Notification** with it.
   **Otherwise**: **Get Dictionary Value** for `detail` from the Contents of
   URL, then **Show Alert** with "Not saved: " followed by it.

## Build: Save link

New Shortcut named **Save link**. Turn on **Show in Share Sheet** and set
**Share Sheet Types** to **URLs** only.

1. **Text** → `http://<address>:5000`.
2. **Ask for Input** (Text), prompt "Note (optional)", as above.
3. **Get Contents of URL**: same URL, **POST**, **JSON** body with
   `url` = the Shortcut Input, `title` = empty, `html` = empty,
   `note` = the Provided Input (all Text).
4. Steps 7 and 8 of **Save page**, unchanged.

## When the server cannot be reached

Shortcuts has no try/catch. If the request cannot connect, iOS stops the
Shortcut and shows its own error ("The operation couldn't be completed",
"Could not connect to the server", or similar). The wording is iOS's, not
ours, and nothing is retried later; share again once the server is back.

## Manual test checklist

Run against a server you can watch (`uv run bookmarks serve`), with the
phone on the same network.

1. **Build.** Both Shortcuts exist, appear in the share sheet, and the
   address action points at the server.
2. **Safari sends the page.** On a logged-in or single-page-app page (a
   Reddit thread), share → **Save page**, skip the note → notification
   "Saved". `list_submissions` (MCP) shows it pending; run
   `bookmarks drain` and the summary describes the page you saw, not a
   login wall.
3. **Another app sends the link only.** From an app other than Safari, share
   a link → **Save link** → "Saved". The server log shows a request with an
   empty `html`.
4. **Note prompt.** Save with a note typed → the item has the note. Save with
   the note left empty → it has none.
5. **Already saved.** Share the same page again with a note → "Already saved
   on <date>; note not added".
6. **Tracking parameters.** Share the same link with `?utm_source=x` added →
   "Already saved on <date>".
7. **Re-queued.** Save a URL that fails (a 404 page), drain until
   `list_submissions` shows it failed, then share it again → "Re-queued".
8. **Rejected URL.** Make **Save link** send something that is not http(s)
   (edit the URL field to `ftp://example.com` for one run) → alert
   "Not saved: not an http(s) URL…".
9. **Server down.** Stop the server and share a link → iOS shows its
   connection error, and the Shortcut stops.
10. **Wrong address.** Point the address at a host that does not answer →
    iOS shows its error; no hang longer than about a minute.
11. **Plain HTTP.** Steps 2 and 3 work over `http://` (not only `https://`).
12. **Away from home.** On cellular without Tailscale, sharing shows iOS's
    connection error; with Tailscale on, it saves.
