# Research: Content Acquisition by Link Type

> Research for issue #10. Answers: for the kinds of links actually in the live
> corpus, where does text worth summarizing come from? Written to inform the
> planned rebuild of this app as an LLM-first recall store (save URL → headless
> `claude -p`/`codex exec` summary → embed for semantic search). Server
> (thunderbird) is headless CPU-only Ubuntu — no browser rendering available
> unless one is installed.

## TL;DR

The live corpus is dominated by three shapes that each need a *different*
acquisition method, plus a long tail that plain server-side HTTP simply
cannot reach:

| Type | Count | Best source |
|---|---|---|
| Articles / blogs / newsletters / news | 33 | Readable-HTML extraction (MarkItDown/BeautifulSoup on raw HTML) — already implemented, works well |
| GitHub / Git-hosting repos | 13 | GitHub REST API (`gh api .../readme`, `gh repo view`) — **not** HTML scraping |
| Docs / reference / wiki sites | 7 | Same readable-HTML extraction, sometimes weaker (framework docs sites often ship little SSR content) |
| App / product / SaaS landing pages | 5 | OpenGraph/Twitter Card meta tags + store metadata APIs, not body text |
| Reddit (forum/social) | 5 | **Cannot be fetched server-side** — old.reddit.com JSON API is the only viable path; current pipeline gets nothing |
| Audio/video (SoundCloud) | 1 | Not applicable — no transcript, metadata only |
| Misc reference/tool page | 1 | Readable-HTML, thin content expected |

No YouTube links exist in the current corpus, but the recommendation for that
type is included below since the user expects more of them.

---

## 1. Corpus survey

**Source:** `/srv/bookmarks-data/bookmarks.js` — a JS file assigning a plain
array literal to `const bookmarks`, 682 lines, 65 bookmark records, read-only
(not modified for this research).

### Schema actually in use

Spot-checking records across the file (not just the first few) shows the
following fields, not all present on every record:

- `url` (string, always present)
- `title` (string, always present — for records added after roughly
  2026-01, this is literally just the URL again, see below)
- `description` (string, always present, but see failure mode below)
- `tags` (array of strings, always present, often just `["unread"]`)
- `dateAdded` (ISO-8601 timestamp with microseconds and UTC offset, always
  present)
- `summarized` (ISO-8601 timestamp, **optional** — only on a handful of the
  oldest records; most records lack it entirely)
- `favorite` (boolean, present on most but not all post-2025-12-05 records;
  absent on older ones)

There is no `folder` field and no separate "notes" field distinct from
`description`. So today's extraction pipeline produces exactly one field
(`description`) that stands in for a summary — there's no raw extracted text
or markdown persisted anywhere; only the LLM's synthesized description
survives.

### Operational finding: the pipeline has been silently failing

For every record added since roughly 2026-03, `title` is a verbatim copy of
the `url` and `description` reads:

```
Error generating description: Failed to generate content for <url>: 401 Client Error: Unauthorized for url: https://api.perplexity.ai/chat/completions
```

`bookmarks/services/llm_providers.py` (`PerplexityProvider`, `PerplexityMCPProvider`)
confirms the pipeline calls Perplexity's `api.perplexity.ai/chat/completions`
for description generation, reading `PERPLEXITY_API_KEY` from the environment.
The 401s indicate that key is missing, expired, or invalid — **not** a
content-extraction failure, since the app's own local extractors
(`HTMLExtractor`/`MarkdownExtractor` in `content_extractor.py`) never touch
Perplexity at all; Perplexity is a separate, optional description-generation
provider layered on top. Roughly 19 of the 65 records (all "unread"-tagged,
dated 2026-03 onward) carry this failure. This is worth flagging to the user
as a live bug independent of this research, but it isn't reproduced here
beyond the error text above (which contains no credential material — nothing
resembling a password, key, or token was found anywhere in `bookmarks.js`).

### Counts by type (65 URLs total)

| Type | Count | Examples |
|---|---|---|
| Articles / blogs / newsletters / news | 33 | `paulkrugman.substack.com/p/we-are-no-longer-a-serious-country`, `thenewstack.io/the-case-against-metrics-for-developer-productivity/`, `newsletter.pragmaticengineer.com/p/frictionless-...`, `www.npr.org/2026/08/10/nx-s1-...`, `blog.cloudflare.com/cloudflare-os/` |
| GitHub repos / Git-hosting | 13 | `github.com/risingwavelabs/risingwave`, `github.com/awesome-selfhosted/awesome-selfhosted`, `github.com/upstash/context7`, `github.com/OpenHands/OpenHands/blob/main/docs/ACP_AGENTS.md`, `codeberg.org/mtlynch/little-moments` |
| Docs / reference / wiki sites | 7 | `sql-flow.com/docs/introduction/basics`, `stylepedia.net/style/` (Red Hat style guide), `thinkinginpython.com/44_Effect_Management.html`, `learn.deeplearning.ai/courses/agent-skills-with-anthropic/...`, `amiga.lychesis.net/` |
| App / product / SaaS landing pages | 5 | `ente.io/de/`, `gethomerun.app/`, `secretspec.dev/`, `tabletopaudio.com/`, `awesomeskill.ai/category` |
| Reddit (forum/social) | 5 | `www.reddit.com/r/selfhosted/comments/1pj1n0p/...`, `www.reddit.com/r/DnD/wiki/world_and_map_generation/`, `www.reddit.com/r/coolgithubprojects/comments/1v509h6/...` |
| Audio/video streaming | 1 | `soundcloud.com/ultimaterpg/sets` |
| Other reference/tool | 1 | `homewyse.com/` (cost-estimator tool site) |

No `youtube.com`/`youtu.be` links exist in the current corpus at all.

---

## 2. Current extraction approach in this repo

- **`bookmarks/services/content_extractor.py`** defines two strategies behind
  a `ContentExtractor` Protocol:
  - `HTMLExtractor` — plain `requests.get()` + `BeautifulSoup(html.parser)`,
    strips `script/style/nav/footer/header`, returns flattened `get_text()`
    capped at 4000 chars. Fast, cheap, loses all structure/links.
  - `MarkdownExtractor` — same fetch, then pipes the raw bytes through
    `MarkItDown().convert_stream()` to get structured Markdown (headings,
    lists, links, tables preserved), capped at a configurable `max_chars`
    (default 8000 in the extractor, CLI default also 8000).
  - Both are plain synchronous HTTP GETs with a browser-spoofing
    `User-Agent` header and a 10s default timeout — **no JS execution, no
    browser**, so anything that needs client-side rendering to produce body
    text will not get any.
- **`bookmarks/cli.py`** exposes both as the `fetch_web_content` console
  script (registered in `pyproject.toml`'s `[project.scripts]`), taking
  `--format {html,markdown}`, `--max-chars`, `--timeout`. This is the tool I
  used below for the live sanity checks — it exercises the exact code path
  the app would use today.
- **`docs/MARKITDOWN_COMPARISON.md`** documents three approaches (adds an MCP
  option calling a `perplexity_ask` MCP tool that offloads fetching entirely
  to Perplexity's server) and recommends MarkItDown as default over
  BeautifulSoup for quality (preserves structure/links, ~20-30% more tokens),
  citing GitHub's own repo page as the "real-world example" where MarkItDown
  allegedly turns the page into a clean structured summary. **My live test
  below shows that example does not hold up in practice** — see §4.

---

## 3. Live sanity checks

Ran the repo's own `fetch_web_content` CLI (`uv run fetch_web_content <url>
--format markdown`) against one representative URL per major type actually in
the corpus. This exercises the real `MarkdownExtractor` code path, not a
theoretical one.

| URL tested | Type | Result |
|---|---|---|
| `alexwlchan.net/2025/mildly-dynamic-websites/` | article/blog | **Clean.** Nav-stripped, real article prose came through immediately, MarkItDown correctly identified the H1 and body. |
| `github.com/risingwavelabs/risingwave` | GitHub repo | **Fails.** Plain GET returns GitHub's *logged-out marketing/nav shell* (Copilot ads, "Sign in", feature menus) — the README content never appears in the captured window; you'd need to fetch much deeper into the page or it isn't server-rendered into the initial HTML in a scrapeable spot at all. This directly contradicts `MARKITDOWN_COMPARISON.md`'s cherry-picked cpython example. |
| `ente.io/de/` | app/product page | **Weak.** Mostly nav links and a stack of `<img>` alt-less hero images; almost no descriptive prose text survives extraction. |
| `sql-flow.com/docs/introduction/basics` | docs site | **Weak.** Modern doc-site framework (Docusaurus/Next-style) — captured output is mostly sidebar/nav links, actual page content is either further down or client-hydrated. |
| `reddit.com/r/selfhosted/comments/1pj1n0p/...` | Reddit thread | **Total failure.** Title extraction fell back to bare domain (`www.reddit.com`) and there was no body text at all — new-Reddit's React shell returns effectively nothing to a plain GET. |
| `learn.deeplearning.ai/courses/.../introduction` | course platform | **Partial success** — this one actually worked; got real lesson-guide prose ("Quick Guide & Tips", numbered steps). Likely because this specific intro/lesson page happens to be server-rendered, unlike a typical SPA dashboard. Not something to rely on as a general rule for this domain. |

Takeaway: readable-HTML extraction is reliable for the article/blog majority
of the corpus, unreliable-to-useless for GitHub, product landing pages, and
Reddit — exactly the cases the task anticipated.

---

## 4. Per-type recommendation

### Articles / blogs / newsletters / news (33 of 65 — the majority)

**Keep the current approach.** `MarkItDown` (already a dependency, already
wired into `MarkdownExtractor`) or `BeautifulSoup` plain-text extraction on
the raw HTTP response is the right tool — no browser needed, confirmed
working live (§3) on a real corpus URL. Primary source for capability
claims: the library's own README —
**https://github.com/microsoft/markitdown** (MarkItDown converts HTML/many
document types to Markdown, preserving headings/lists/links/tables, per the
"Overview" section of that README). No change recommended here beyond fixing
the Perplexity-key regression noted in §1.

If markdown quality on messier blogs becomes an issue later, `trafilatura`
(readability-style boilerplate removal, MIT-licensed, pure Python, no
browser) is the well-sourced alternative — see its own docs at
**https://trafilatura.readthedocs.io/** — but nothing in this corpus's live
test suggested this is currently needed.

### GitHub repos / Git-hosting (13 of 65)

**Do not scrape the HTML — use the GitHub REST API.** The live test in §3
shows a plain GET returns marketing chrome, not the README, confirming this
is a real gap, not a theoretical one. Two calls suffice:

- `gh api repos/{owner}/{repo}` — repo metadata (description, stars, primary
  language, topics, homepage, last-push date). Documented at
  **https://docs.github.com/en/rest/repos/repos** ("Get a repository").
- `gh api repos/{owner}/{repo}/readme` — returns the rendered/raw README
  content (base64-encoded raw, or ask for `Accept:
  application/vnd.github.raw+json` for plain text). Documented at
  **https://docs.github.com/en/rest/repos/contents** ("Get a repository
  README").
- Equivalently, `gh repo view {owner}/{repo} --json description,stargazerCount,...`
  wraps the same API for a single CLI call, per `gh`'s own manual.

This handles 12 of the 13 repo bookmarks directly. The one outlier,
`github.com/OpenHands/OpenHands/blob/main/docs/ACP_AGENTS.md`, points at a
specific file inside a repo rather than the repo root — for that shape, use
`gh api repos/{owner}/{repo}/contents/{path}` (same Contents API as above) to
fetch that exact file's content instead of the repo README.
`codeberg.org/...` is a self-hosted Gitea/Forgejo instance, not GitHub, so the
GitHub REST API does not apply there — Codeberg exposes its own compatible
API (Forgejo/Gitea `/api/v1/repos/{owner}/{repo}` and
`/api/v1/repos/{owner}/{repo}/readme`), but that's a smaller slice (1 of 65
URLs) and worth only a fallback-to-HTML-extraction if not implemented.

### Docs / reference / wiki sites (7 of 65)

Same readable-HTML extraction as articles, but expect it to work less
reliably — §3's `sql-flow.com` test shows a modern docs-site framework can
return mostly sidebar nav rather than page content on a plain GET, whereas
`learn.deeplearning.ai`'s specific intro page happened to work. There's no
single fix here without a browser; treat this bucket as "best effort,
readable-HTML extraction, verify per-domain" rather than a solved case.

### App / product / SaaS landing pages (5 of 65)

**Don't try to extract body text — extract metadata.** §3 confirms plain-GET
HTML on `ente.io` yields almost no descriptive prose (mostly nav + images).
The right source is the meta tags every product/marketing page ships for
link-preview purposes:

- **OpenGraph** (`og:title`, `og:description`, `og:image`, `og:site_name`) —
  primary source: the protocol's own spec at **https://ogp.me/** ("The Open
  Graph protocol enables any web page to become a rich object in a social
  graph" — defines the exact meta-tag vocabulary to parse).
- **Twitter/X Card** tags (`twitter:title`, `twitter:description`,
  `twitter:image`) as a fallback when OpenGraph tags are absent — primary
  source: **https://developer.x.com/en/docs/x-for-websites/cards/overview/markup**.
- For actual App Store / Play Store listing pages specifically (none in the
  current corpus, but the user mentioned bookmarking "apps/products"
  generally): Apple's **iTunes Search API**
  (**https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html**)
  gives free, keyless JSON metadata (description, category, rating) for any
  public App Store listing by app ID or bundle ID. Google does **not**
  offer an equivalent public read API for arbitrary Play Store listings — the
  **Google Play Developer API**
  (**https://developers.google.com/android-publisher**) only covers apps you
  own/publish yourself — so for third-party Play Store URLs, OpenGraph tags
  on the listing page (Play Store pages do carry them) are the only
  server-side option.

Both OpenGraph and Twitter Card tags are just `<meta>` elements already
present in the raw HTML `MarkdownExtractor`/`HTMLExtractor` already fetch —
this needs a small addition to `content_extractor.py` (a meta-tag-first
extraction path, falling back to body text only if no OG/Twitter tags exist),
not a new fetch mechanism.

### Videos — YouTube etc. (0 of 65 today, but anticipated)

No YouTube links exist in the corpus right now, but since the user expects
more, the primary-source-backed answer is: **prefer a transcript library over
scraping the watch page**, and be aware of a real constraint on the official
API path.

- `youtube-transcript-api` (Python, no API key, works by calling YouTube's own
  internal timedtext/caption-track endpoints) is the pragmatic default — it's
  explicitly designed for exactly this ("retrieve the transcript/subtitles
  for a given YouTube video... does **not** require a headless browser, like
  other selenium-based solutions do" per its own README at
  **https://github.com/jdepoix/youtube-transcript-api**). This matches the
  CPU-only, no-browser server constraint directly.
- The **official** path, YouTube Data API v3's `captions` resource
  (**https://developers.google.com/youtube/v3/docs/captions**), documents a
  `captions.download` endpoint — but its own reference notes downloading a
  caption track requires OAuth 2.0 authorization, and in practice succeeds
  only for videos the authenticated account owns/manages (third-party videos
  largely aren't downloadable this way). So the official API is not
  actually usable for arbitrary bookmarked videos; `youtube-transcript-api` (or
  equivalent scraping of the public timedtext endpoint) is the realistic
  choice, with the caveat that it depends on an undocumented endpoint that
  YouTube could change without notice.

### Types that cannot be fetched server-side

Confirmed by live testing (§3), not just inferred:

- **Reddit threads/wikis (5 of 65)** — `reddit.com/r/selfhosted/comments/...`
  returned **zero body text** on a plain GET in the live test; new-Reddit's
  UI is a client-hydrated React app, and Reddit also actively rate-limits/
  blocks non-browser user agents. (A possible partial mitigation without a
  browser — swapping the domain to `old.reddit.com`, which is still mostly
  server-rendered HTML, or Reddit's own read JSON API at
  `reddit.com/r/{sub}/comments/{id}.json` — was not tested here since it's an
  implementation detail beyond this research's live-fetch budget, but it's
  worth a follow-up spike rather than writing Reddit off entirely.)
- **App/product landing pages beyond metadata (5 of 65)** — OpenGraph/Twitter
  tags give a title+one-line description, but if the user wants a genuine
  *content* summary of a marketing page's actual pitch (not just the
  meta-description), that text often lives behind client-side rendering
  (React/Vue marketing sites, e.g. `ente.io`'s hero section rendered almost
  entirely as background images in the live test) and a plain GET won't
  surface it.
- **JS-rendered SPA docs/course platforms** — `sql-flow.com`'s docs and (in
  general, though not proven for the one page tested) platforms like
  `learn.deeplearning.ai` are built on client-hydrating frameworks; whether a
  plain GET gets useful text is inconsistent per-page, not a reliable rule.
- **Anything login-walled** — none of the 65 corpus URLs are behind an
  explicit paywall or login wall today (no LinkedIn, X/Twitter status pages,
  or private-repo links present), but the architecture should assume this
  will recur (the user mentioned bookmarking things broadly). Paywalled news,
  LinkedIn posts, X/Twitter posts, and private GitHub repos share the same
  fix.
- **The fix for all of the above:** none of these can be solved by a
  smarter *server-side* fetch — headless Chromium/Playwright would help with
  the SPA cases but not the login-walled ones, and installing a browser on a
  CPU-only headless box is exactly the cost the user wants to avoid. The
  actual fix is architectural: the **browser-extension capture client**
  (mentioned in the user's plan) should optionally send the *rendered* page's
  extracted text/HTML at save time — captured from the user's own already-
  authenticated, already-JS-executed browser tab — as an alternative to a
  server-side fetch. The server-side extractor stays the default path for the
  ~85% of the corpus (articles, docs, GitHub via API, OG tags) where it works
  cleanly; the extension-capture path is the fallback specifically for
  Reddit/login-walled/heavily-client-rendered pages.

---

## 5. Summary table

| Type | Corpus count | Method | Primary source |
|---|---|---|---|
| Articles/blogs/newsletters/news | 33 | MarkItDown/BeautifulSoup on raw HTML (existing) | github.com/microsoft/markitdown |
| GitHub repos | 13 | `gh api repos/{owner}/{repo}` + `.../readme` (or `.../contents/{path}`) | docs.github.com/en/rest/repos/repos, /rest/repos/contents |
| Docs/reference/wiki | 7 | Same as articles; unreliable per-domain | (same as above) |
| App/product/SaaS pages | 5 | OpenGraph + Twitter Card meta tags; iTunes Search API for App Store | ogp.me; developer.x.com cards markup; developer.apple.com iTunes Search API |
| Reddit | 5 | **Cannot server-side fetch reliably** — extension capture, or spike `old.reddit.com`/`.json` API | (n/a — architectural gap) |
| YouTube (0 today, anticipated) | 0 | `youtube-transcript-api`; official Data API v3 captions mostly unusable for third-party videos | github.com/jdepoix/youtube-transcript-api; developers.google.com/youtube/v3/docs/captions |
| SPA/login-walled generally | — | Extension-capture client sends rendered text at save time | (n/a — architectural gap) |

No secrets were encountered beyond the (already-visible, already-invalid)
Perplexity 401 error strings baked into `bookmarks.js`'s `description`
fields — no passwords, keys, or tokens were found anywhere in the corpus or
the codebase reviewed for this research.
