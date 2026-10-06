# How to work in this repo

Constraints, not a checklist. When two conflict, pick the lowest future cost for this repo and say so in the commit.
The hard invariants are the strict form. Adapted from Tomas Vykruta's AGENTS.md rules (Sep 2026).

## Design principles (every file)

- **Separation of concerns.** Domain rules in their owners (table below). Mechanisms, such as the drain, decide how
  and when work runs, never what an outcome means. Transport in the adapters (`web/app.py`, `mcp_server.py`,
  `cli.py`). Schema in `db.py`. Name the one concern of the file you edit.
- **Encapsulation.** Read another module's tables through its functions, never with your own SQL.
- **One rule change touches one module.**
- **DRY means one home.** Grep before writing a rule, threshold, format string or schema fact; extend the home.
  Do not abstract coincidental similarity.
- **KISS / YAGNI.** Function over class. A `Protocol` exists only where a test fake replaces it. No speculative
  flags, hooks or layers. Boring tech.
- **Single responsibility.** If you describe it with "and", split it. Names say intent; comments say why, with a date.
- **Depend on contracts.** Core modules never import `fastapi`, `mcp`, `httpx` or `subprocess`. Every outside
  system (clock, HTTP, LLM, embedder) arrives as a Protocol the composition root hands in.
- **Fail fast, and fail closed.** Validate at the edges. On any security or authorization path an error is a refusal,
  never a pass.
- Composition over inheritance · open/closed only where change has happened twice · no `a.b.c.d` reaching ·
  optimize for deletion.

## Hard invariants

1. **One owning module per domain.** Domains are the terms in `CONTEXT.md`. Consolidate a scattered domain before adding to it. Add a row when you confirm
   an owner; never add a second owner. A function-level import to dodge a cycle means the logic is in the wrong
   module.

   Two systems (ADR 0002): the **store** and **ingestion**, which lives in `bookmarks.ingest`. Ingestion reaches the
   store only through its public functions; the store never imports `bookmarks.ingest` (enforced by `tests/test_import_direction.py`).

   | System | Domain | Owner |
   |---|---|---|
   | Store | Item (identity, record, Note), Type | `store.py` |
   | Store | Search (filters, ranking) | `search.py` |
   | Store | Embedding | `embed.py` |
   | Ingestion | Submission, Stage, Status (stage order, what an outcome means, retry budget, re-saving a failed URL) | `ingest/lifecycle.py` |
   | Ingestion | Source text (the retrieving stage) | `ingest/retrieve.py` |
   | Ingestion | Summary, Entities, Provenance (the summarising stage) | `ingest/summarise.py` |
   | Ingestion | Saving (outcomes and messages) | `service.py` **(moves into `ingest/`)** |

   Mechanisms own no domain rules: `ingest/drain.py` runs stages within the `claude -p` budget; schema in `db.py`,
   settings in `settings.py`, the LLM adapter in `ingest/llm/`. Helpers are called only by their owner:
   `fetch.py`, `extract.py`, `github.py` by `ingest/retrieve.py`.

2. **Never duplicate logic.** On the second use: (1) move it to the owner, (2) switch the original caller, tests
   green, no behaviour change, (3) then build the new use. Grep the expression and list every copy; the move
   switches them all or the commit names each one left and why. A helper beside old copies is one more duplicate.
   Any behaviour change is its own commit. Same for schemas: one fact, one column.
3. **No business logic in transport.** A FastAPI handler, MCP tool or CLI command validates input, calls
   an owner, and translates the result. MCP tool docstrings are contract, not logic. Templates render; they
   decide nothing.
4. **A refactor never weakens a check.** Refusals, fail-closed paths, signature and key checks keep their exact
   semantics. If a refactor changes what is refused, it is not a refactor.
5. **Secrets never enter git.** A secret found in history is rotated, not just removed.

## How to work

- **Measure first.** Before refactoring a system, review it against these rules with numbers: every file, every
  copy, the longest functions. Write the baseline down; report against it afterwards.
- **Refactor first, then change.** When a change would add a second copy, grow a module past its one concern, or
  cross a domain boundary: a behaviour-preserving refactor with tests green first, then the change, as separate
  commits.
- **Move code verbatim, and prove it.** Use a script, not hand edits, to move a function. Prove the moved code is
  identical by comparing `ast.dump()` before and after. Anything the script cannot prove safe, it refuses.
- **A move includes its imports.** The body can be identical while a rebuilt import is wrong:
  `from x import a as b` rewritten as `from x import b`. Python raises `ImportError` at import time, so the boot
  check catches it — but only if every module is imported.
- **Gates, not promises.** A rule that matters is enforced by a test, a lint, a scan or a hook, not by a sentence
  in this file. One script runs every gate in sequence and must end green before any deploy **(not built)**:
  1. a boot check: import every `bookmarks.*` module, build the FastAPI app and the MCP server, assert `/api/items`
     and the `search` tool are registered, run `bookmarks --help` **(not built)**;
  2. undefined names: `uv run ruff check .` (`F821`);
  3. the full test suite: `uv run pytest`, always against the real schema via `db.connect`, never a hand-written one;
  4. a shape test: no handler or MCP tool over N lines; no core module imports `fastapi`, `mcp`, `httpx` or
     `subprocess` **(not built)**;
  5. a security scan: gitleaks (pre-commit), `pip-audit` for vulnerable dependencies **(not built)**, and no
     `*.db`, `.env` or `data/` file tracked **(not built)**.
  A check whose tool is missing reports SKIPPED, never pass. Never claim a check passed that was not run.
- **No exemptions.** When a gate fires on a real case, fix the case. Do not add an allowlist to silence it. A list
  of known legacy offenders may exist only if it can only shrink.
- **Deploy is self-reverting.** Pull, restart, probe and revert happen in one command **(not built)**.
- **A probe is not a test.** After a deploy that touches a critical path, exercise it end to end: capture → drain →
  embed → MCP search. A route that answers 200 proves it is registered, not that it works. A real drain makes paid
  `claude -p` calls; say so before running one.
- **Untracked files are invisible to scanners that read the index.** Stage new files before running the gates.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on varigg/bookmarks, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `CONTEXT.md` plus `docs/adr/`. See `docs/agents/domain.md`.
