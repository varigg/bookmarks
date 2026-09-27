# adventure-library reuse research (ticket #9)

Primary source: `/home/varigg/code/adventure-library` (read-only for this
research; local repo on this machine, git history not required — all
citations below are file paths and, where useful, line numbers/function
names in that repo as it stood on 2026-09-27).

Context: the bookmarks rebuild is an LLM-first recall store — saving a URL
keeps it, a headless `claude -p`/`codex exec` call drained from a queue
summarises each item, summaries are embedded for semantic search, and an
agent over MCP is the main interface. adventure-library already runs the
analogous machinery for RPG PDFs: job queue + drain, local embeddings,
sqlite-vec + FTS5 hybrid search, and an MCP server. This note assesses each
for reuse.

## Verdict summary

| Component | Verdict | Why (one line) |
|---|---|---|
| Job queue + drain | **Extract into a shared package** | `llm_job`/`llm_job_attempt` schema, claim/complete/retry protocol, and the `ClaudeCodeCLIProvider` subprocess wrapper are already domain-agnostic; only the task-type handlers are RPG-specific. |
| Embeddings | **Extract into a shared package** | `EmbeddingProvider` protocol + sentence-transformers/Ollama backends + `ProviderCache`/circuit breaker operate on abstract `(target_type, target_id)`, not RPG concepts. |
| sqlite-vec + FTS5 hybrid search | **Extract the generic core; ignore the RPG-specific ranking leg** | RRF fusion, FTS5 external-content trigger pattern, and sqlite-vec-as-distance-function loading are generic; the facet-preference leg and compatibility-scalar gates are pure RPG taxonomy. |
| MCP server | **Copy the pattern, not the tool surface** | FastMCP + per-call session + provider-cache singleton + docstring-as-spec are tiny and reusable; all 17 tools are RPG-named and 9 of them are taxonomy-curation tools bookmarks has no analog for. |

Full detail, file-by-file, follows. The "do not inherit" list is consolidated
at the end.

## 1. Job queue + drain

**Verdict: extract into a shared package.** The queue table, claim protocol,
and provider-adapter/failure-classification layer contain zero RPG-specific
logic — they operate on an opaque `task_type` string and a JSON `payload`.
Only the *handlers* registered against those task types (`module_triage`,
`module_metadata`, `reuse_index`) are domain-specific, and those live in a
separate file (`worker.py`'s `_handle_*` functions) that a shared package
would not take.

**Key files:**
- `src/adventure_library/jobs.py` — the queue itself. `enqueue()` (line 139,
  idempotent via unique identity index, `ON CONFLICT DO NOTHING RETURNING`),
  `claim_next()` (196) / `claim_by_id()` (208) (atomic `UPDATE ... WHERE
  status='pending' ... RETURNING`, no broker), `recover_stale()` (232,
  requeues rows stranded `running` by a killed drain — concurrency-of-one
  makes them unambiguously stale), `complete()` (247), `record_attempt()`
  (263), `abandon()` (315) / `retry()` (335) — durable parking via a single
  conditional `UPDATE ... WHERE status IN ('pending','failed') RETURNING`
  (not select-then-update, so a concurrent claim race reports a clean
  rejection instead of clobbering a `running` row), and the
  `supersede_pending_*` family (35, 64, 80) that retires stale-identity
  pending jobs when a newer version/re-extraction/module-removal makes them
  moot.
- `src/adventure_library/migrations.py` — schema. `llm_job` (line 148):
  `id, task_type, payload, input_hash, schema_version, prompt_version,
  provider, model, status CHECK(status IN ('pending','running','done',
  'failed','abandoned') — the 5th value added at line 283), attempts,
  priority, started_at, completed_at, failure_class, failure_message,
  raw_result_path, created_at`; unique index on `(task_type, input_hash,
  schema_version, prompt_version)` (168) is the idempotent-enqueue identity;
  `idx_llm_job_claim ON (status, priority, id)` (170) backs the atomic claim.
  `llm_job_attempt` (305) records one row per attempt (duration, turn count,
  outcome, failure class/message) for audit and the circuit breaker.
- `src/adventure_library/worker.py` — the job runner. `run_one()` (553) is
  the single-job execution path shared by both callers: run one claimed
  job's handler, record the `llm_job_attempt` row, append a log record. It
  handles four outcome branches uniformly (success, `ProviderFailure`,
  `invalid_output`, `task_error`). `run_drain()` (706) loops `run_one` over
  `jobs.claim_next()`'s priority order for `intake drain [--limit N]
  [--until HH:MM]`; it recovers stale `running` rows at startup and trips a
  **circuit breaker after 5 consecutive LLM failures** (instant-failure
  outages stop after one job's damage, not the whole queue's retry budget).
  `intake process JOB_ID...` (CLI, see `cli.py`) claims and runs exactly the
  named pending jobs, independently, via `run_one` directly — no stale-row
  recovery, since it claims by id.
- `src/adventure_library/llm/provider.py` — `LLMProvider` protocol,
  `LLMRequest`/`LLMResult`/`ProviderFailure` dataclasses. Failure
  classification (`auth`, `rate_limit`, `unavailable`, `timeout`,
  `invalid_output`, `transient`) runs over the CLI's *full* output (both
  streams on non-zero exit, the whole JSON envelope on `is_error`) —
  documented as a fix for a real blind spot (error text landing on stdout
  with silent stderr).
- `src/adventure_library/llm/claude_cli.py` — `ClaudeCodeCLIProvider` (class
  at line 55) is the actual subprocess wrapper: shells out to `claude -p
  --output-format json` (lines 69-94) with per-request `--max-turns`,
  `--tools` (restricts the built-in toolset, unlike `--allowedTools` which
  only auto-approves), `--add-dir`, and `--strict-mcp-config` on every call
  (no `--mcp-config`, since an empty one is rejected by newer CLI versions —
  this alone removes a measured ~30K-token MCP tool-definition overhead per
  call). A `single_turn` mode additionally forces `--tools ""` (explicit
  zero-tools sentinel) and strips `CLAUDECODE` from the child env so a
  `claude -p` shelled out from inside a Claude Code session doesn't
  recognize itself as nested — directly relevant to bookmarks, which plans
  the same "headless `claude -p`/`codex exec` from a drain" deployment shape.
  `subprocess.run` with a timeout; `TimeoutExpired` becomes a `timeout`
  failure class. This is essentially the exact primitive bookmarks needs for
  its own summarization calls — a `codex exec` adapter would be a sibling
  class behind the same `LLMProvider` protocol.

**Coupling to the RPG domain:** none in the queue/runner/provider layers
themselves. The only domain-specific code is `worker.py`'s three
`_handle_module_triage` / `_handle_module_metadata` / `_handle_reuse_index`
functions (build an RPG-specific prompt, apply an RPG-specific result
schema) and the `supersede_pending_for_module`/`_reextraction` call sites in
`hierarchy.py`/`ingest.py`. Task-type strings, per-task-type priority and
timeout policy, and the size-scaled `reuse_index` timeout formula are all
adventure-library's own tuning, not part of the mechanism.

**Do not inherit:**
- The three RPG task-type handlers and their prompt-building — bookmarks
  needs exactly one handler shape ("summarize this URL's content").
- The size-scaled timeout formula tuned for markdown-file byte counts from
  PDF extraction — bookmarks' inputs (web pages) are a different size
  distribution; re-derive rather than copy the constants.
- The `module_triage` single-turn/zero-tools call shape is *worth keeping as
  a pattern* (an unattended summarization call over untrusted web content
  should also run with an empty tool list and `CLAUDECODE` stripped) but the
  triage-specific prompt content itself is not.
- The retired `queue_state`/pause-resume machinery (ADR/changelog: "Since
  #166 nothing is persisted on a stop") is already dead code in
  adventure-library itself — a design lesson (don't build a persisted pause
  state; let a released job just sit `pending`) rather than something to
  port.

## 2. Embeddings

**Verdict: extract into a shared package.** The provider abstraction, both
concrete backends, and the caching/circuit-breaker wrapper are already
generic over `target_type`/`target_id` — they know nothing about modules,
components, or RPG content.

**Key files:**
- `src/adventure_library/embeddings.py` — `EmbeddingProvider` Protocol
  (~line 26, `embed(texts) -> vectors`, `.dims`, `.backend`, `.model`);
  `SentenceTransformersProvider` (34) wraps a local `sentence-transformers`
  model, default `DEFAULT_SENTENCE_TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"`
  (line 20) — a 384-dimension, ~80MB model, dimension read at runtime via
  `model.get_sentence_embedding_dimension()` (line 50-53), never hard-coded;
  `OllamaProvider` (67) talks to `http://127.0.0.1:11434` (`DEFAULT_OLLAMA_URL`,
  line 22) with default model `nomic-embed-text` (`DEFAULT_OLLAMA_MODEL`,
  line 21) and a fixed `DEFAULT_OLLAMA_DIMS = 768` (line 23) since Ollama's
  embed endpoint doesn't self-report dims up front — true dims are
  discovered lazily on the first real `embed()` call and re-read rather than
  trusted (documented at lines 333-336, because Ollama's lazy discovery
  differs from sentence-transformers' upfront one); `CircuitBreakerProvider`
  (152) wraps either backend with a 60s cooldown and single-flight probing
  (only one caller contacts a failing backend; concurrent callers fail fast);
  `ProviderCache` (202) is the process-wide lazy singleton construction
  wrapper shared by the web app, MCP server, and worker — construction
  failure is permanently cached as unavailable until process restart.
  `knn()` (476-504) is the brute-force cosine-distance query (see component
  3 below).
- Backend selection is via `ADVENTURE_LIBRARY_EMBED_BACKEND` /
  `ADVENTURE_LIBRARY_EMBED_MODEL` env vars (referenced in
  `docs/deployment.md`); switching backend/model requires `intake embed
  --force` to re-embed everything, since vectors are keyed to
  `(backend, model, dims)` in the `embedding` table's unique index — the
  schema treats a model change as a distinct, non-overlapping vector space,
  never silently mixing dimensions.
- Storage: `embedding` is a **plain table**, not a sqlite-vec `vec0` virtual
  table — see component 3.

**CPU timing:** adventure-library's docs document the *KNN scan* step as
"single-digit milliseconds at this scale" (`docs/architecture/retrieval.md`,
"Embeddings are CPU-local" section) but **do not separately benchmark the
encode step** (turning text into a vector) on CPU. No number for
sentence-transformers' `all-MiniLM-L6-v2` encode latency on this class of
hardware is recorded anywhere in the repo (checked `CHANGELOG.md`,
`docs/deployment.md`, `experiments/model-comparison/README.md` — that
experiment benchmarks LLM extraction quality/cost, not embedding speed).
This is a **gap**, not a finding: `all-MiniLM-L6-v2` is a widely-benchmarked
lightweight model (~22M params) that typically encodes a short text in
single-digit-to-low-double-digit milliseconds on a modern CPU core, but that
figure is from the model's own reputation, not from anything measured on
thunderbird in this codebase. If precise timing matters for the bookmarks
design, it should be measured directly (the sentence-transformers package is
already a dependency choice worth reusing either way).

**Coupling to the RPG domain:** minimal. The only RPG-specific fact baked in
is *what text gets embedded* — "module title + synopsis" / "component title
+ summary" (`docs/architecture/retrieval.md`) — decided by the caller, not
by `embeddings.py`. The provider layer itself takes arbitrary text.

**Do not inherit:** nothing structural; the two-target-type
(`module`/`component`) embedding split has no bookmarks analog (bookmarks
are one flat entity type), so a shared package should genericize
`target_type` down to a single kind, or drop it.

## 3. sqlite-vec + FTS5 hybrid search

**Verdict: extract the generic mechanics into a shared package; ignore the
RPG-specific ranking leg entirely.**

**Key files:**
- `src/adventure_library/db.py` — `_load_sqlite_vec()` (17-32) and
  `connect()` (35-48): `sqlite-vec` is loaded as a precompiled PyPI package
  (`sqlite-vec>=0.1.6`), via `conn.enable_load_extension(True)` →
  `sqlite_vec.load(conn)` → disable again. **Only `vec_distance_cosine`, a
  scalar function, is used — the `vec0` virtual-table/index feature is
  deliberately not used.** `docs/architecture/retrieval.md` states this
  explicitly as a documented, deferred future optimization: "a vec0 index is
  deliberately NOT used." In other words, sqlite-vec here is nothing more
  than a distance-function library over a plain `BLOB` column — much
  lighter than "vector index" implies, and directly portable to bookmarks at
  a similar (personal-scale) corpus size.
- `src/adventure_library/migrations.py` — `embedding` table (132-146, plain
  table, not `vec0`) and the FTS5 setup (180-241): `module_fts`/
  `component_fts` are ordinary **external-content** FTS5 virtual tables
  (`content='module', content_rowid='id'`), synced by six triggers
  (`module_ai/ad/au`, `component_ai/ad/au`) using the standard
  insert-on-insert / delete-marker-then-reinsert-on-update FTS5 pattern —
  and four more triggers (`module_embedding_stale`, `module_embedding_delete`
  + component equivalents) that `DELETE FROM embedding` whenever embedded
  fields change or the row is deleted, invalidating stale vectors (no
  auto-re-embed trigger; a background sweep, `intake embed`, re-embeds).
- `src/adventure_library/search.py` — `_rrf_scored()` (364-386) is pure,
  generic reciprocal-rank fusion: for each named ranked-id list, `score[id]
  += 1/(60+rank)`, dedupe within a list, order by `(-score, first_seen)`.
  **Zero RPG logic** — feed it `("fts", ids)` + `("vector", ids)` and it
  works for bookmarks unchanged. `_hybrid_rows()` (523-586) and
  `_materialize_hits()` (589-605) are the shared executor
  (candidates → facet leg → FTS → lazy provider construction → KNN with
  degrade-on-any-exception → RRF → materialize/limit/truncate) — generic in
  shape, but its facet-leg step (`_facet_leg_ids`, 458-514) is the one
  RPG-specific stage (see below). `hybrid_search_modules`/
  `hybrid_search_components` (683, 796) are the two concrete instantiations.
- `src/adventure_library/embeddings.py` — `knn()` (476-504) is the KNN
  query itself: `SELECT target_id FROM embedding WHERE target_type=? AND
  backend=? AND model=? AND dims=? AND length(vector)=? AND target_id IN
  (candidate_ids) ORDER BY vec_distance_cosine(vector, ?) ASC LIMIT ?` — a
  brute-force scan restricted first to a SQL/facet-filtered candidate set.
- ADRs worth citing directly: **038** (search-result contract — `score` +
  `legs`/`leg_ranks` visible to the caller, so degradation is observable, not
  silent); **039** (search takes a provider *factory*, invoked at most once,
  only when a query token and non-empty candidate set exist — token-free
  browse requests never pay embedding-construction cost — directly reusable
  discipline); **043** (facets bias, never gate — "no campaign-fit score is
  computed, an app ranks relevance, an agent judges fit" — the RPG-specific
  facet leg this section says to skip).

**Coupling to the RPG domain:** the fusion math, the FTS5 trigger pattern,
the sqlite-vec loading code, and the KNN query are domain-agnostic — they
already operate on abstract `target_type`/`target_id`. What's RPG-specific
is layered on top as a **third ranking leg**: the facet-preference leg (a
five-vocabulary system — `genre`/`setting`/`tone`/`environment`/`mode` —
tied to `term`/`term_alias`/`module_term`/`component_term` tables and a full
propose/approve/merge/reject curation workflow, ADR-036/ADR-043), plus hard
SQL gates on compatibility scalars (game system, experience tier, level,
`kind`) and the module/component two-grain split (whole document vs.
extracted NPC/location/set-piece sub-entities — a "reuse index" concept with
no bookmarks analog).

**Do not inherit:**
- The five-vocabulary facet-preference leg and its curation workflow — built
  for RPG taxonomy curation; wildly oversized for whatever tagging (if any)
  bookmarks needs.
- The module/component two-grain split — bookmarks are flat; no sub-entity
  "reuse index" concept is needed.
- `kind`-awareness (`campaign`/`adventure`/`supplement`/`compilation`/
  `magazine`) and `parent_id` hierarchy filtering — no bookmarks analog.
- Compatibility-scalar hard gates (game system/tier/level) — pure RPG
  filters.
- **Worth inheriting as precedent, explicitly:** the "vec0 deliberately not
  used" decision. At personal-bookmark-collection scale, a brute-force
  cosine scan over a BLOB column is almost certainly still fine — don't
  reach for a real vector index prematurely.

## 4. MCP server

**Verdict: copy the implementation pattern, not the tool surface.** The
whole server is 335 lines; the plumbing (framework choice, connection
lifecycle, provider caching, error convention) is generic and tiny enough to
re-type rather than literally import, but the 17 exposed tools are almost
entirely RPG-shaped and over half of them (9/17) are a taxonomy-curation
surface bookmarks has no version of.

**Key file:** `src/adventure_library/mcp_server.py` (335 lines, the entire
server).

**Framework:** the official Anthropic `mcp` Python SDK
(`mcp[cli]>=1.28.1,<2` in `pyproject.toml`), specifically its bundled
high-level `mcp.server.fastmcp.FastMCP` class (**not** the separate
third-party `fastmcp` PyPI package). `mcp = FastMCP("adventure-library")`;
tools are registered with plain `@mcp.tool()` decorators on type-hinted
functions returning `dict`; the server runs over stdio via `mcp.run()`,
launched as `adventure-library mcp` and registered into Claude
Code/Codex by the user (`docs/architecture/retrieval.md`, "What each surface
exposes").

**Tool surface (17 total):**
- Search/retrieval (reusable *shape*, RPG-named): `search_adventures`,
  `get_adventure`, `search_components`, `get_component`, `get_source_pages`.
- Ops (reusable shape): `list_pending_jobs`.
- Vocabulary curation (**9 of 17** — over half the surface, entirely
  RPG-specific): `discover_vocabulary`, `approve_term`, `merge_term`,
  `reject_term`, `approve_system`, `merge_system`, `reject_system`,
  `list_proposed_terms`, `list_proposed_systems`.

**Generic infra patterns worth lifting (as pattern, not code — each is a
handful of lines):**
- `_session()` context manager (~lines 30-39): opens/closes exactly one DB
  connection per tool call via `db.session(settings.db_path)`; tests replace
  this seam with a non-closing shared connection.
- Module-level lazy singleton + lock for the embedding provider
  (`_provider_cache`, `_get_embedding_provider`, ~lines 15-27):
  double-checked locking around `embeddings.ProviderCache(..., breaker=True)`
  so a down backend costs one stall per cooldown window, not one per tool
  call.
- Error convention: tools just `raise ValueError(...)` on bad input; the
  FastMCP SDK itself converts that to a protocol-level tool error — **no
  custom error-wrapping code exists in the server at all.**
  Thinness-as-pattern: the file's own docstring calls itself "a thin adapter
  over the service layer... Tools return structured results with IDs and
  evidence, not only prose" — every tool body is `with _session() as conn:
  return <service_function>(conn, ...)`, zero business logic in the MCP
  layer.
- Docstring-as-spec: tool docstrings carry the actual contract (valid enum
  values, error conditions, filter semantics) because that's what the
  calling agent reads — a deliberate duplication with the service-layer
  docstrings (tracked as its own spec item, held together by
  docstring-pinning tests).

**Coupling to the RPG domain:** the search/retrieval tools' *naming* and
*shape* are RPG-specific (the file even keeps the name "adventure" over the
renamed internal "module" service layer as acknowledged naming debt — not a
pattern worth inheriting). `get_source_pages` is a PDF-page-marker
provenance mechanism ("read the scene behind a hit," capped at 5 pages, with
`total_pages` derived from page markers) with no bookmarks analog — a
bookmarks equivalent would fetch saved page content or the original URL,
not walk PDF page markers. The 9-tool curation surface is entirely the
five-vocabulary taxonomy's MCP face.

**Do not inherit:**
- The 9-tool curation surface — bookmarks' design (summarize + embed, agent
  does semantic recall) has no analogous need for a human
  propose/approve/merge/reject taxonomy workflow, at least not in v1.
- The two-tool-pair split (`search_X`+`get_X` × modules and components) —
  bookmarks are one flat entity type, so one search+get pair suffices.
- `get_source_pages`'s page-window provenance mechanism — a different
  provenance shape (fetched page content, or the saved URL) fits bookmarks.

## Consolidated "do not inherit" list

Complexity that exists in adventure-library specifically because the domain
is RPG PDFs/campaigns, and that the bookmarks rebuild should consciously
skip rather than try to generalize away:

1. **The five-vocabulary facet-preference system** (`genre`/`setting`/
   `tone`/`environment`/`mode`) and its full propose/approve/merge/reject
   curation workflow (ADR-036, ADR-043) — a taxonomy-curation UI/workflow
   built for tagging RPG content against a controlled vocabulary. If
   bookmarks wants tags at all, start much smaller.
2. **The module/component two-grain data model** — a whole-document vs.
   extracted-sub-entity ("reuse index": NPCs, locations, encounters, hooks)
   split. Bookmarks are flat URLs; there's no sub-entity extraction concept
   to port.
3. **`kind`-awareness and `parent_id` hierarchy** (`campaign`/`adventure`/
   `supplement`/`compilation`/`magazine`, self-referential parent, depth 2,
   `sequence`) — a filing/hierarchy model for RPG products with no
   bookmarks analog.
4. **Compatibility-scalar hard gates** (game system, experience tier,
   level) — pure RPG relevance filters.
5. **PDF-page-marker provenance** (`get_source_pages`, the 5-page-window
   cap, `total_pages` from page markers) — specific to serving "the scene
   behind a hit" from a converted PDF's markdown. Bookmarks' provenance
   (the saved page/URL) is a different shape entirely.
6. **The size-scaled `reuse_index` job timeout formula** tuned to markdown
   byte counts from PDF extraction — not the right shape for web-page
   summarization inputs.
7. **The retired `queue_state` pause/resume table** — already dead code in
   adventure-library itself (see `worker.py`'s changelog note, "#166");
   don't resurrect it as a pattern.

## What generalizes cleanly (recap)

For contrast, the pieces assessed above as "extract into a shared package"
or "copy the pattern" are already written against abstract concepts
(`target_type`/`target_id`, a `task_type` string, a `Job`/`LLMProvider`
protocol) rather than RPG nouns: the `llm_job`/`llm_job_attempt` queue
schema and claim/complete/retry protocol (`jobs.py`, `worker.py`), the
`ClaudeCodeCLIProvider` subprocess wrapper (`llm/claude_cli.py`) — a strong
starting point for both a `claude -p` and a `codex exec` adapter behind one
`LLMProvider` protocol — the `EmbeddingProvider` protocol with its two
backends and circuit-breaker cache (`embeddings.py`), the FTS5
external-content trigger pattern and sqlite-vec-as-distance-function loading
(`migrations.py`, `db.py`), the reciprocal-rank-fusion function
(`search.py:_rrf_scored`), and the MCP server's connection-per-call +
provider-cache-singleton + docstring-as-spec pattern (`mcp_server.py`).
