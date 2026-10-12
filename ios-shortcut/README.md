# Bookmarks for iPhone

Two Shortcuts that save a link from the share sheet to the bookmarks
server's capture API (`POST /api/items`). They are built by hand in the
Shortcuts app; iOS will not import an unsigned shortcut file, so this
document is the deliverable.

| Shortcut | Appears for | Sends |
|---|---|---|
| **Save page** | Safari web pages | `url`, `title`, the rendered `html`, `note` |
| **Save link** | links shared from any other app | `url`, `title` and `html` empty, `note` |

Why two: the page's rendered HTML comes from Shortcuts' "Run JavaScript on
Web Page" action, which only works on a Safari web page and fails on a plain
link. iOS picks the Shortcut by what is being shared, so nothing has to
branch. In Safari's share sheet both are listed; choose **Save page**.

The rendered page lets the server keep pages it cannot fetch itself (Reddit,
single-page apps, logged-in pages), the same as the Firefox extension.

> Built and tested on an iPhone on 2026-10-12. The action and menu names
> below are the ones that phone showed; a different iOS version may word
> them differently. The **checklist** at the end says which steps were run.

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
`http://<address>:<port>`. Names that only the Windows/Samba network knows
(NetBIOS, e.g. a bare `thunderbird`) do not resolve on iOS. Away from home
the server is reachable only over Tailscale or a VPN to your network. To
check the address first, open `http://<address>:<port>/docs` in Safari on
the phone; if that page loads, the Shortcut can reach the server.

The address is typed in full, port included, in the **Get contents of**
action. A missing port sends the request to port 80, where nothing answers:
iOS shows no error and the Shortcut simply ends without a notification.

## iOS quirks to expect while building

- **Share types.** Turning on **Show in Share Sheet** (the ⓘ details) adds a
  first action, **Receive [types] from Share Sheet**. Tap the blue types in
  it (it may read "Apps and 18 more"), tap **Clear** in the **Shortcut
  Input** list, then tick only what the Shortcut should accept.
- **Dragging.** Long-press an action to drag it, for example into an **If**
  branch.
- **Variable names.** An output is named after its action. Tap an output
  token to rename it (here, **Reply** for the response of **Get contents
  of**).
- **No text after a variable in the URL field.** A variable fills the whole
  field, so type the full address instead.
- **The reply is typed File.** iOS treats the response as a file, so its
  `message` cannot be picked directly. Add **Get Value for `message` in
  Reply** (search "Get Dictionary"), then use **Select Variable** to pick
  that action's orange output, named **Message**.
- **Set the Type to Text.** When iOS offers a File property on a picked
  output (the **If** line showed "File Size"), tap the token, open **Type**
  and choose **Text**. The condition then reads **Message has any value**.
- **Doubled values.** Picking a variable for a JSON field can leave the
  token in it twice, and the server then stores the text twice ("Test Note
  Test Note"). After filling a field, check that it holds exactly one token.
- **Grey placeholders** (such as the grey **Dictionary**) did not pass the
  previous output along. Pick the variable explicitly.

## Build: Save link

New Shortcut named **Save link**. Turn on **Show in Share Sheet** and accept
**URLs** only (see Share types above).

1. **Receive URLs from Share Sheet** (added automatically).
2. **Ask for Input** (Text), prompt "Note (optional)". An empty answer
   followed by Done is accepted and skips the note. **Cancel stops the whole
   Shortcut and saves nothing.**
3. **Get contents of** `http://<address>:<port>/api/items`. Expand it:
   Method **POST**, Request Body **JSON**, and four Text fields: `url` =
   **Shortcut Input**, `title` = empty, `html` = empty, `note` = **Ask for
   Input**. Rename its output **Reply**.
4. **Get Value for `message` in Reply**.
5. **If** the **Message** output (Type: Text) **has any value**: **Show
   notification** with **Message**.
6. **Otherwise**: **Get Value for `detail` in Reply**, then **Show Alert**
   with "Not saved: " followed by the **Detail** output (Type: Text).

## Build: Save page

Duplicate **Save link** (long-press it → Duplicate) and name the copy **Save
page**. Then:

1. In the **Receive** action, tap **Clear** and accept **Safari web pages**
   only.
2. After it, add **Run JavaScript on Web Page** (input: **Shortcut Input**)
   with exactly:
   ```js
   completion(document.documentElement.outerHTML);
   ```
3. Add **Get Details of Safari Web Page** (input **Shortcut Input**), Detail
   **Page URL**, then a second one with Detail **Name** (the title).
4. In the JSON of **Get contents of**, change the fields (Select Variable,
   Type: Text each time): `url` = **Page URL**, `title` = **Name**, `html` =
   the JavaScript result, `note` stays **Ask for Input**.

## When the server cannot be reached

Shortcuts has no try/catch. If the request cannot connect, iOS stops the
Shortcut and shows its own error. The wording is iOS's, not ours, and
nothing is retried later; share again once the server is back.

## Checklist

Run against a server you can watch (`uv run bookmarks serve`), with the
phone on the same network. Use a scratch database (`BOOKMARKS_DB`) and a
spare port to leave a live server alone. "Run" means done on a phone on
2026-10-12.

1. **Build.** Both Shortcuts exist, appear in the share sheet, and the
   address action points at the server. *Run.*
2. **Safari sends the page.** Share a page from Safari → **Save page**, skip
   the note → "Saved". The submission holds the title and the rendered HTML
   (a 450 KB page arrived intact). *Run.* Still open: on a logged-in or
   single-page-app page (a Reddit thread), `bookmarks drain` produces a
   summary of the page you saw, not a login wall. The drain makes paid
   `claude -p` calls.
3. **Another app sends the link only.** From an app other than Safari, share
   a link → **Save link** → "Saved"; the submission has no HTML. *Run.*
4. **Note prompt.** Save with a note typed → the item has the note. Save with
   the note left empty → it has none. *Run.*
5. **Already saved.** Share the same page again with a note → "Already saved
   on <date>; note not added".
6. **Tracking parameters.** Share the same link with `?utm_source=x` added →
   "Already saved on <date>".
7. **Re-queued.** Save a URL that fails (a 404 page), drain until
   `list_submissions` shows it failed, then share it again → "Re-queued".
8. **Rejected URL.** Set the `url` field of **Save link** to
   `ftp://example.com` for one run → alert "Not saved: not an http(s)
   URL…". *Run.*
9. **Server down.** Stop the server and share a link → iOS shows its
   connection error, and the Shortcut stops.
10. **Wrong address.** Point the address at a host that does not answer →
    iOS shows its error; no hang longer than about a minute.
11. **Plain HTTP.** Steps 2 and 3 work over `http://` (not only `https://`).
    *Run.*
12. **Away from home.** On cellular without Tailscale, sharing shows iOS's
    connection error; with Tailscale on, it saves.
