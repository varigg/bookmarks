# Research: subscription CLI limits for headless summarisation

- **Ticket:** [varigg/bookmarks#8](https://github.com/varigg/bookmarks/issues/8), part of the wayfinder map [#7](https://github.com/varigg/bookmarks/issues/7)
- **Question:** Can `claude -p` (Claude Code, Claude subscription) and `codex exec` (Codex CLI, ChatGPT subscription) carry batch summarisation of bookmarks headlessly, at a corpus of a few hundred items with a handful of new saves per day?
- **Date:** 2026-09-27
- **CLI versions checked locally:** Claude Code 2.1.283, Codex CLI 0.157.1 (`claude --version` / `codex --version`)

## Verdict

**Yes — at this project's scale (a few hundred items total, a handful of new saves a day), both `claude -p` on a Claude Pro/Max subscription and `codex exec` on a ChatGPT Plus/Pro subscription can carry unattended batch summarisation, with `claude -p` the stronger-evidenced and better-tooled choice, and a real (unresolved-by-documentation) terms-of-use question on the OpenAI side worth the user's own risk call.**

- **Volume fits easily under either provider's documented limits.** Anthropic's Pro/Max plans meter on a shared 5-hour + weekly window across Claude and Claude Code combined, with no numeric cap published but explicit confirmation that "ordinary, individual usage" is the intended envelope — a handful of short single-turn calls a day is far below anything that framing is aimed at. OpenAI's own pricing page gives a concrete number: even the cheapest Plus-tier model (GPT-6 Luna, the model this project should use anyway) allows 350–3,000 CLI messages per 5-hour window — several orders of magnitude more than needed.
- **Both companies explicitly ship subscription-backed, non-interactive authentication as a supported CLI path** — Anthropic via `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` (built for "CI pipelines, scripts, or other environments where interactive browser login isn't available") and its own GitHub Actions cron integration using that same token; OpenAI via ChatGPT-login sessions that self-refresh without re-opening a browser. Neither is a workaround — both are documented, first-party mechanisms.
- **Terms of service: Anthropic is clean, OpenAI has one open question.** Anthropic's Claude Code legal page explicitly carves out "an end user... signing in to the unmodified Claude Code binary with their own Claude subscription" from its automated-access restrictions, which otherwise target third parties reselling subscription access. OpenAI has no equivalent carve-out: its Terms of Use ban "automatically or programmatically extract[ing]... Output," worded broadly enough to describe `codex exec` literally, with no document anywhere exempting personal CLI use from it. In context this reads as aimed at bulk scraping/resale rather than personal automation of one's own account via OpenAI's own shipped tool — but that is inference, not a quotable exemption, and the user should treat it as a real (if probably low-risk) open question rather than a settled "yes."
- **Per-call overhead is real but manageable, and asymmetric between the two CLIs.** Both tools load roughly 12–14K tokens of context by default (measured directly: ~11.9K for Claude Code, ~14.5K for Codex, on a trivial prompt with zero MCP servers configured) — this is baseline system-prompt/tool-schema weight, not something a small corpus's content adds much to. Claude Code can be brought close to zero non-prompt overhead (`--tools ""` removes all built-in tools; `--strict-mcp-config` removes all MCP servers — adventure-library measured the latter alone at ~30K tokens saved when MCP servers *are* registered) and the remaining system-prompt cost can be replaced entirely with a short custom one via `--system-prompt`. Codex CLI has no equivalent lever for its intrinsic shell/`apply_patch` tool schema or for AGENTS.md discovery — its floor is higher and less controllable.
- **Recommendation:** lead with `claude -p` (Haiku, single-turn, own system prompt, `--strict-mcp-config`) as the primary summariser, mirroring adventure-library's already-proven `ClaudeCodeCLIProvider` pattern almost directly. Treat `codex exec` (Luna) as a fallback/second provider for when Claude's window is exhausted or as a cross-check, exactly as the project's own map issue (#7) already anticipates ("Codex later"), and flag the ToU ambiguity to the user before wiring it in for real.

## 1. Usage/rate limits on headless invocations

### Claude Code / Claude subscription

- Pro and Max plans meter usage on a **rolling 5-hour session window** plus a **weekly window across all models**, both resetting on a schedule tied to the account. (Source: [support.claude.com — Usage limit best practices](https://support.claude.com/en/articles/9797557-usage-limit-best-practices))
- "Both Pro and Max plans offer usage limits that are shared across Claude and Claude Code, meaning all activity in both tools counts against the same usage limits." Max plan tiers (Max 5x $100/mo, Max 20x $200/mo) use the same 5-hour/weekly mechanic and explicitly bundle Claude Code under "one unified subscription." (Sources: [Use Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan), [What is the Max plan?](https://support.claude.com/en/articles/11049741-what-is-the-max-plan))
- None of those three help-center pages distinguish interactive terminal use from headless/`-p`/scripted use — the limit mechanics are described generically, with no automation carve-out either way.
- The one place headless use is addressed for limit purposes: **"Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK."** (Source: [code.claude.com — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance), "Usage policy → Acceptable use"). This doesn't prohibit scripted/cron use, but signals the advertised numbers are calibrated for a human typing at a keyboard, not for scripted volume.
- Anthropic's own **costs** docs count scheduled/automated invocations the same as interactive turns: "a scheduled task fires on its interval even while the session is idle, sending your full context each time," and the `/usage` breakdown has a dedicated "Loops" row tracking `/loop`-or-other-scheduled-task token consumption. (Source: [code.claude.com — Manage costs effectively](https://code.claude.com/docs/en/costs)) — i.e. scheduled/headless runs are ordinary metered usage, not a separate class, and not treated as against policy.
- **Anthropic explicitly ships and documents subscription-backed non-interactive auth for exactly this use case:** `claude setup-token` generates a one-year OAuth token described as "for CI pipelines, scripts, or other environments where interactive browser login isn't available," which "requires a Pro, Max, Team, or Enterprise plan" and is set as `CLAUDE_CODE_OAUTH_TOKEN`. (Source: [code.claude.com — Authentication](https://code.claude.com/docs/en/authentication)) Anthropic's Claude Code GitHub Actions integration uses the identical token to run on a `schedule:` cron trigger under subscription billing. (Source: [code.claude.com — Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)) A bare-metal Ubuntu cron job calling `claude -p` with `CLAUDE_CODE_OAUTH_TOKEN` set is mechanically identical to this sanctioned pattern — Anthropic's built-in scheduling surfaces (cloud Routines, Desktop scheduled tasks, `/loop`) just don't happen to include "plain cron" as a named option. (Source: [code.claude.com — Run prompts on a schedule](https://code.claude.com/docs/en/scheduled-tasks))
- Caveat: `CLAUDE_CODE_OAUTH_TOKEN` is **not read in `--bare` mode** — "If your script passes `--bare`, authenticate with `ANTHROPIC_API_KEY` or an `apiKeyHelper` instead." (Source: [code.claude.com — Authentication](https://code.claude.com/docs/en/authentication)) So the CLI's own lowest-overhead startup flag is incompatible with subscription billing — see §3.

### Codex CLI / ChatGPT subscription

- Codex usage is metered on a **5-hour rolling window**, with a **weekly cap also potentially applying on top** — both windows are confirmed to exist by OpenAI help articles on reset mechanics, but no page discloses the numeric weekly cap. (Sources: [help.openai.com — How banked Codex resets work](https://help.openai.com/en/articles/20001498-how-banked-codex-resets-work), [.../Paid Work and Codex rate limit resets](https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets))
- The general explainer for using Codex on a ChatGPT plan defers to the pricing page for actual numbers, and states usage varies by "model, where the task runs, task complexity, context, reasoning, speed, and tools." (Source: [help.openai.com — Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan))
- **The pricing page gives a concrete numeric table** for local (CLI) messages per 5-hour window, by plan and model (Source: [learn.chatgpt.com/docs/pricing](https://learn.chatgpt.com/docs/pricing)):

  | Model | Plus | Pro 5x | Pro 20x |
  | --- | --- | --- | --- |
  | GPT-6 Astra | 5–45 | 25–225 | 100–900 |
  | GPT-6 Sol | 15–150 | 70–700 | 300–3,000 |
  | GPT-6 Luna | 350–3,000 | 1,750–14,000 | 7,000–56,000 |

  "Local messages and cloud chats share your plan's usage allowance" — CLI and cloud/web draw from the **same** pool, not metered separately. Even the cheapest Plus tier (GPT-6 Luna: 350–3,000 messages per 5-hour window) comfortably covers a handful of short summarisation calls a day.
- **Not confirmed anywhere:** an explicit statement that limits apply identically to `codex exec` vs. the interactive TUI. Every doc implies a single shared allowance with no headless/interactive distinction, but none states this as a deliberate design decision about headless mode specifically.
- **Authentication persistence for cron:** "For sign in with ChatGPT sessions, Codex refreshes tokens automatically during use before they expire, so active sessions usually continue without requiring another browser login." No exact token lifetime is published, so how much idle time between cron runs it tolerates is unconfirmed and worth testing empirically. OpenAI's own docs mildly *prefer* API-key auth for "programmatic Codex CLI workflows, such as CI/CD jobs," but do not state ChatGPT-login auth is disallowed or unsupported for `codex exec` — this reads as a preference, not a restriction. (Source: [learn.chatgpt.com/docs/auth](https://learn.chatgpt.com/docs/auth))

## 2. Terms of use for automated personal use

### Anthropic

- **Consumer Terms of Service**, effective October 8, 2025, §3, prohibits accessing the Services "through automated or non-human means, whether through a bot, script, or otherwise" — *except* "when you are accessing our Services via an Anthropic API Key or **where we otherwise explicitly permit it**." (Source: [anthropic.com/legal/consumer-terms](https://www.anthropic.com/legal/consumer-terms)) Read literally this clause looks like it could bar a cron script — but Anthropic's own Claude Code legal page (below) explicitly treats subscription-authenticated Claude Code itself, including its documented scripting/CI paths, as within the "explicitly permit it" carve-out. This clause targets unauthorized bots/scraping of claude.ai, not Anthropic's own shipped product feature.
- **Usage Policy**, effective September 15, 2025: no clause specifically addresses personal automated/scripted use or headless-vs-interactive use. The closest relevant clause bars "coordinating malicious activity across multiple accounts to avoid detection or circumvent product guardrails" — aimed at abuse/evasion, not a single legitimate account's personal cron job. (Source: [anthropic.com/legal/aup](https://www.anthropic.com/legal/aup))
- **Claude Code legal page** directly addresses the boundary that matters here: OAuth authentication "is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code." The restriction that follows targets *third-party developers* — "Anthropic does not permit third-party developers to... route requests through Free, Pro, or Max plan credentials on behalf of their users" — and explicitly carves out the single-user case: "Nor does it prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription..." (Source: [code.claude.com/docs/en/legal-and-compliance](https://code.claude.com/docs/en/legal-and-compliance))
- **Net read:** no clause names "cron," "scheduled," or "headless" as prohibited; the automated-access ban is qualified by "where we otherwise explicitly permit it," and Anthropic's own product (setup-token, GitHub Actions scheduling, the costs page's scheduled-task accounting) explicitly documents and supports subscription-authenticated scripted/scheduled invocation. This is inference across documents, not one directly quotable "personal cron is allowed" sentence — flagged as such. A few hundred short summaries with a handful of new saves a day reads as squarely "ordinary, individual usage," not the volume the one soft caveat in §1 seems aimed at.

### OpenAI

- **Terms of Use** (effective January 1, 2026), "What you cannot do," verbatim: "Automatically or programmatically extract data or Output," and "Interfere with or disrupt our Services, including circumvent any rate limits or restrictions or bypass any protective measures or safety mitigations." (Source: [openai.com/policies/row-terms-of-use](https://openai.com/policies/row-terms-of-use/)) **This is the one real ambiguity found in either provider's terms**: read literally, "automatically or programmatically extract... Output" describes exactly what `codex exec` does. In context with the rest of the prohibited-uses list (reverse engineering, illegal use, misrepresenting AI content as human, training competing models) it reads as aimed at bulk scraping/resale, not personal automation via OpenAI's own shipped CLI — but no OpenAI document explicitly carves that exception out the way Anthropic's Claude Code legal page does for Claude Code. This is a genuine gap in the primary sources, not something resolvable by inference alone.
- **Account/registration clause**, same ToU: "You may not share your account credentials or make your account available to anyone else." This is about sharing credentials with *another person*, not automating one's own account, and doesn't on its face restrict a personal cron job under one's own login.
- **OpenAI Account Sharing Policy** explicitly permits multi-device use ("using your account on multiple devices... though usage limits may apply") and is silent on CLI/automated use specifically. (Source: [help.openai.com — OpenAI Account Sharing Policy](https://help.openai.com/en/articles/10471989-openai-account-sharing-policy))
- **Usage Policies** page has no explicit automation/bot/cron clause; the closest generic language is "circumventing our safeguards" under a "Protect people" heading. (Source: [openai.com/policies/usage-policies](https://openai.com/policies/usage-policies/))
- **Net read:** no OpenAI document explicitly names "Codex CLI + cron + personal ChatGPT subscription" as permitted or forbidden. Unlike Anthropic (which has a directly-on-point carve-out for Claude Code's own scripted paths), OpenAI's broad "programmatic extraction" clause is the one open risk flagged in this research — worth the user's own judgment call, not a settled primary-source answer either way.

## 3. Per-call overhead (latency, default context)

### Claude Code — measured

One live smoke test, run from `/tmp` (no project `CLAUDE.md`, no MCP servers configured), with everything except `--model`/`--tools`/`--strict-mcp-config` left at CLI defaults (i.e. the **default system prompt was not overridden**):

```
claude -p "Reply with exactly: OK" --model haiku --tools "" --strict-mcp-config --output-format json
```

Result (fields from the `--output-format json` envelope):

| Metric | Value |
| --- | --- |
| Wall time (`time`) | 2.69 s real |
| API latency (`duration_api_ms`) | 962 ms |
| Time to first token (`ttft_ms`) | 957 ms |
| Total turn duration (`duration_ms`) | 1017 ms |
| Input tokens (fresh) | 10 |
| **Cache-creation input tokens** | **11,933** |
| Output tokens | 39 (33 of which `thinking_tokens`) |
| Model actually used | `claude-haiku-4-5-20251001` |
| Reported cost (subscription; informational only) | $0.024071 |

Even with `--strict-mcp-config` (no MCP servers loaded) and `--tools ""` (no built-in tools), the call still paid **~11.9K tokens of cache-creation input** — this is the *default Claude Code system prompt/environment block* (cwd, git status, platform info, etc.), which is loaded whenever `--system-prompt` is not passed to override it. It is billed as prompt-cache-write only on the first call in a session; a real batch job that keeps reusing the same fixed system prompt across many single-turn calls would hit 1h/5m ephemeral cache (visible in `cache_creation.ephemeral_1h_input_tokens` above) and pay the cheaper cache-read rate on repeats — *if* Claude Code's cache write/read windows persist between separate `claude -p` process invocations from cron (unconfirmed locally; each invocation is a fresh process, and whether the API-side prompt cache still hits depends on Anthropic's server-side cache TTL, not the CLI).

**This confirms adventure-library's finding (see §4) empirically: an unmodified default system prompt is the dominant per-call overhead, not the built-in tool definitions or MCP.** Passing an explicit, short `--system-prompt` (as adventure-library's provider does, and confirmed present in this project's local `claude --help`: `--system-prompt <prompt>  System prompt to use for the session`) should collapse this ~12K-token overhead to whatever that custom prompt costs.

Anthropic's own docs corroborate the mechanism without giving a number: a `-p` session "loads the same context an interactive session would, including anything configured in the working directory or `~/.claude`" unless mitigated — CLAUDE.md auto-discovery, hooks, skills, custom commands, subagents, plugins, and any MCP servers registered in `.mcp.json`/`~/.claude.json` all load by default, with **no workspace-trust dialog or per-server approval prompt in `-p` mode** (i.e. they load silently). MCP tool *definitions* specifically are "deferred by default" — only names/short instructions enter context until a tool is actually invoked — which is a separate, smaller mitigation from `--strict-mcp-config`'s "don't load the servers at all." (Sources: [code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless), [.../costs](https://code.claude.com/docs/en/costs))

### Codex CLI — measured

One live smoke test, run from `/tmp` (no project, no MCP servers registered — confirmed via `codex mcp list` → "No MCP servers configured yet"), default model (`gpt-6-astra`, from `~/.codex/config.toml`), no `--model` override:

```
codex exec --skip-git-repo-check --sandbox read-only --json "Reply with exactly: OK"
```

Result (from the `turn.completed` JSONL event):

| Metric | Value |
| --- | --- |
| Wall time (`time`) | 4.53 s real |
| Input tokens | 14,473 |
| **Cached input tokens** | 12,160 |
| Output tokens | 5 |
| Model used | `gpt-6-astra` (default; no `-m` override) |

With zero MCP servers configured, the ~14.5K input tokens are pure baseline overhead: Codex's built-in developer/system instructions plus its shell/`apply_patch` tool schemas, which — unlike Claude Code's `--tools ""` — **`codex exec` has no documented flag to strip**; the shell tool is intrinsic to the agent loop. `--sandbox read-only` only constrains what that tool may do, not whether its schema is sent. Also note: `codex exec` without piped stdin printed `Reading additional input from stdin...` and blocked briefly waiting for stdin — a cron invocation must close/redirect stdin (e.g. `</dev/null`) or pass `-` deliberately to avoid a hang.

### CLI flags for a minimal invocation

**Claude Code (`claude -p`):**

| Flag | Effect |
| --- | --- |
| `-p` / `--print` | Non-interactive, single response, exits |
| `--model <alias\|full-id>` | Force model. Current aliases (per [code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config)): `default`, `best`, `fable`, `sonnet`, `opus`, `haiku`, `sonnet[1m]`, `opus[1m]`, `opusplan`. `haiku` is documented as "the fast and efficient Haiku model for simple tasks" — the target for cheap batch summarisation (matches this project's own smoke test, which resolved to `claude-haiku-4-5-20251001`). Aliases "resolve to the recommended version... and update over time" — pin a full model name (e.g. `claude-haiku-4-5`) instead of the alias if a cron script needs a stable model across months |
| `--tools ""` | Documented sentinel disabling **every** built-in tool (Bash, Edit, Read, …) |
| `--strict-mcp-config` (with no `--mcp-config`) | Loads **zero** MCP servers, ignoring `~/.claude.json` — adventure-library measured this alone as removing ~30K tokens of MCP tool-definition overhead per call (see §4) |
| `--system-prompt <text>` | **Overrides** the default system prompt outright — needed to avoid the ~12K-token default-prompt overhead measured above |
| `--output-format json` | Structured envelope (`result`, `usage`, `is_error`, `subtype`, `num_turns`) for programmatic parsing |
| `--max-turns 1` | Caps agentic turns; irrelevant once tools are disabled but cheap insurance |
| `--exclude-dynamic-system-prompt-sections` | Strips per-machine sections (cwd, env, memory paths, git status) from the system prompt into the first user message, improving cross-call prompt-cache reuse — only applies with the **default** system prompt (ignored once `--system-prompt` is set) |
| `--bare` | Minimal mode: skips hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, CLAUDE.md auto-discovery. Anthropic calls this "the recommended mode for scripted and SDK calls" and says it will become the default for `-p`. **But it does not read `CLAUDE_CODE_OAUTH_TOKEN` (or keychain OAuth)** — bare mode requires `ANTHROPIC_API_KEY`/`apiKeyHelper` instead, i.e. **`--bare` is incompatible with subscription billing** and must not be used for this use case ([code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless), [.../authentication](https://code.claude.com/docs/en/authentication)) |

**Codex CLI (`codex exec`):**

| Flag | Effect |
| --- | --- |
| `exec` | Non-interactive subcommand (alias `e`) |
| `-m`/`--model <model>` | Force model, e.g. `-m gpt-6-luna` (see model names below) |
| `-s read-only` / `--sandbox read-only` | No filesystem/network writes needed for a summarisation prompt |
| `--skip-git-repo-check` | Required when running outside a git repo (e.g. a cron working directory) |
| `--ignore-user-config` | Skip `$CODEX_HOME/config.toml` entirely (auth still comes from `$CODEX_HOME`) — avoids picking up any interactively-registered MCP servers or profile settings |
| `-c mcp_servers.<id>.enabled=false` | The only **documented** way to disable MCP servers is per-server, via the general `-c key=value` override. There is no literally-documented blanket "disable all MCP servers" syntax (a bare `-c mcp_servers={}` is a plausible construction from the override mechanism, not something OpenAI's docs show as an example) — in practice, if nothing is registered (`codex mcp list` → "No MCP servers configured yet", confirmed locally) or `--ignore-user-config` is used, this is moot |
| `-c approval_policy=never` | Never prompt for command approval. Valid values are `"on-request"` and `"never"` (a granular object form also exists); OpenAI's docs flag `"untrusted"` as unsupported and `"on-failure"` as deprecated — stale blog examples referencing either are outdated. There is **no dedicated `--ask-for-approval` flag on `exec`** — it's config-only, unlike top-level `codex`'s `-a` flag |
| `--json` | JSONL event stream (`thread.started`, `item.completed`, `turn.completed` with `usage`) for programmatic parsing |
| `-o`/`--output-last-message <file>` | Write just the final message to a file — convenient for a summarisation pipeline |
| `--ephemeral` | Don't persist session/rollout files to disk (cron hygiene) |
| *(no equivalent to `--tools ""`)* | `codex exec`'s shell/apply-patch tool schema is intrinsic; there is no documented flag to omit it, unlike Claude Code |
| *(no equivalent to `--strict-mcp-config`)* | AGENTS.md auto-discovery also has no documented on/off switch (only a 32 KiB `project_doc_max_bytes` cap and filename customisation) — mitigate by running from a directory with no AGENTS.md and no MCP servers registered, rather than a CLI flag |

A synthesized minimal unattended invocation, built from the individually-documented flags above (not itself a literal example from OpenAI's docs): `codex exec --skip-git-repo-check --ignore-user-config --sandbox read-only -c approval_policy=never -m gpt-6-luna --ephemeral -o out.txt "<prompt>" </dev/null`.

### Model names (Codex)

Per `learn.chatgpt.com/docs/models` (reference date 2026-09-27): **GPT-6 Astra** (`gpt-6-astra`, most capable/expensive, the default in this project's local `~/.codex/config.toml`), **GPT-6 Sol** (`gpt-6-sol`, mid-tier, "complex coding and agentic workflows"), and **GPT-6 Luna** (`gpt-6-luna`) — explicitly described as "our most efficient model for focused, high-volume tasks, **including summarization, extraction**... best for clear, repeatable tasks," and the cheapest/highest-allowance tier in the pricing table above. **`gpt-6-luna` is the one to force via `-m` for this project's bookmark-summarisation job.** GPT-5.4/5.4-mini were retired from ChatGPT-sign-in Codex on 2026-08-31, replaced by Sol/Luna; GPT-5.5 retires 2026-10-14. No "codex-mini"/"gpt-5-mini"-style model is available under ChatGPT sign-in — those exist only as separate, per-token API model IDs.

## 4. What adventure-library learned (`/home/varigg/code/adventure-library`)

Adventure-library (the sibling project this rebuild is modelled on) already runs `claude -p` headlessly from a cron-friendly job queue (`intake drain`) and has hit exactly the failure modes this ticket asks about. Source: `src/adventure_library/llm/claude_cli.py`, `src/adventure_library/llm/provider.py`, `docs/architecture/jobs.md`, `docs/adr/000-legacy-decision-log.md` (decision 5), `docs/adr/042-big-document-reuse-index-pages-only.md`.

- **Decision (ADR log #5):** "First extraction provider: Claude CLI (`claude -p`); Codex later" — the same subscription-CLI-first choice this rebuild is making.
- **Invocation shape** (`claude_cli.py`): `claude -p --output-format json --max-turns N --system-prompt "<own prompt>" [--tools ...|--tools ""] [--add-dir ...] --strict-mcp-config [--model <model>]`, run via Python `subprocess.run(..., input=user_prompt, capture_output=True, timeout=...)` from a fresh per-call `tempfile.mkdtemp()` cwd (cleaned in a `finally`).
- **MCP overhead is real and was measured, not assumed:** a bare `claude -p` "otherwise loads whatever MCP servers the caller's `~/.claude.json` registers, measured at ~30K tokens of tool-definition overhead per call" — this is why `--strict-mcp-config` is applied unconditionally on every call the provider builds, no exceptions.
- **`--mcp-config "{}"` is not a safe belt-and-suspenders:** newer CLI versions reject an empty JSON object as invalid (it wants a top-level `mcpServers` key), so the provider relies on `--strict-mcp-config` alone (with no `--mcp-config` at all) to get zero MCP servers.
- **A stronger isolation mode for untrusted/unattended single-turn calls** (`LLMRequest.single_turn`): forces `--tools ""` (the documented sentinel for zero tools — *merely omitting* `--tools` leaves the default toolset reachable) and pops `CLAUDECODE` from the subprocess's env so a `claude -p` shelled out from **inside** a Claude Code session doesn't mistake itself for a nested session. Bookmark summarisation (single page fetch → one summary, no repo tools needed) is exactly this shape.
- **Own system prompt, not the default:** every call passes an explicit `--system-prompt`, sidestepping the ~12K-token default-prompt overhead this research measured directly (§3).
- **Rate-limit detection is text-matching, not a documented API:** failures are classified by scanning **both** stdout and stderr for markers — `"rate limit"`, `"usage limit"`, `"overloaded"`, `"quota"`, `"limit reached"` → classified `rate_limit`; `"not logged in"`, `"authentication"`, `"/login"`, `"unauthorized"` → classified `auth`. Anything else defaults to `transient`. This is a workaround, not a documented contract — Anthropic does not publish a structured rate-limit error code for the CLI that adventure-library found; **string-matching the CLI's human-readable error text is the only mechanism in use.**
- **Pause, don't burn retries, on a cap hit:** `auth`, `rate_limit`, and `unavailable` are `PAUSE_CLASSES` — the job is released back to `pending` and the whole drain stops immediately (`provider_stopped`), rather than retrying and burning the job's retry budget against what is likely a subscription cap that needs real wall-clock time to reset. A circuit breaker additionally stops the drain after 5 consecutive LLM failures of any kind.
- **Scheduling is deliberately aligned to subscription usage windows:** `intake drain [--limit N] [--until HH:MM]` is described in the architecture doc as "for cron-friendly scheduling against subscription usage windows" — i.e. the project already assumes Anthropic's subscription rate limit resets on a schedule (consistent with Anthropic's documented 5-hour/weekly windows, see §1) and paces cron runs to it rather than trying to run everything at once.
- **The CLI's own JSON envelope, not the exit code alone, carries the real signal:** `claude -p` writes its result envelope to stdout **even on a non-zero exit**, and the envelope's key order (`usage`/`modelUsage` before `result`) means a naively-bounded log excerpt can truncate before reaching the field that explains the failure — adventure-library had to widen its truncation handling after being bitten by this.
- **Latency for a real (non-trivial) tool-driven call is minutes, not seconds:** unrelated to a plain single-turn summary, but for scale: adventure-library's *tool-driven, multi-turn* `reuse_index` analysis (Read/Grep over a full document) runs a 900s-to-1800s size-scaled timeout (ADR 042) — because that call lets the model use tools across many turns. A bookmark summary in `single_turn` mode (no tools, one short page of content) is architecturally the cheap case this research measured directly in §3, not this expensive case.
- **Not yet migrated/used by adventure-library:** a Codex (`codex exec`) provider adapter — decision 5 says "Codex later," and no `codex_cli.py`-equivalent exists in the current source tree. There is no in-repo prior art for `codex exec` specifically; only `claude -p` has a working, battle-tested adapter to borrow from.

## 5. Recommended invocation for this project

**Primary: Claude Code, single-turn, Haiku.** Follow adventure-library's `ClaudeCodeCLIProvider` shape directly (`src/adventure_library/llm/claude_cli.py`):

```
claude -p \
  --output-format json \
  --max-turns 1 \
  --system-prompt "<bookmarks-specific summariser prompt>" \
  --tools "" \
  --strict-mcp-config \
  --model haiku
```
— piped the page content as stdin (`input=` in `subprocess.run`), run from a fresh per-call `tempfile.mkdtemp()` cwd, with `CLAUDE_CODE_OAUTH_TOKEN` set in the cron environment (from `claude setup-token`, one-time interactive setup) rather than relying on keychain OAuth, and with `CLAUDECODE` popped from the subprocess env (adventure-library's `single_turn` isolation) so a nested-session self-detection never triggers. Classify failures by scanning both stdout+stderr for `rate limit`/`usage limit`/`overloaded`/`quota`/`limit reached` (pause and stop, don't retry) vs. `not logged in`/`authentication`/`/login`/`unauthorized` (auth failure) vs. everything else (transient/retryable) — there is no structured error code to key off instead, per adventure-library's own experience.

**Fallback/second provider: Codex CLI, Luna.**

```
codex exec \
  --skip-git-repo-check \
  --ignore-user-config \
  --sandbox read-only \
  -c approval_policy=never \
  --model gpt-6-luna \
  --ephemeral \
  --json \
  "<prompt>" </dev/null
```
— redirect stdin from `/dev/null` (or pipe the page content deliberately) to avoid the observed stdin-wait hang; parse the `turn.completed` JSONL event's `usage` block the way Claude Code's envelope is parsed. No adventure-library prior art exists for this provider yet — this project would be the first to write and battle-test a `codex_cli.py`-equivalent adapter.

**Pacing:** size a cron `intake drain`-style batch well under the smaller of the two confirmed 5-hour windows (Anthropic's numeric cap isn't published; OpenAI's cheapest-tier floor is 350 messages/5hr on Plus) — at a few-hundred-item corpus with a handful of daily saves, a single daily or twice-daily drain run comfortably clears either provider's window with enormous headroom, so no special throttling logic is needed beyond adventure-library's existing pause-on-rate-limit behaviour.

## Sources

**Anthropic / Claude Code:**
- [support.claude.com — Usage limit best practices](https://support.claude.com/en/articles/9797557-usage-limit-best-practices)
- [support.claude.com — Use Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
- [support.claude.com — What is the Max plan?](https://support.claude.com/en/articles/11049741-what-is-the-max-plan)
- [code.claude.com — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [code.claude.com — Manage costs effectively](https://code.claude.com/docs/en/costs)
- [code.claude.com — Authentication](https://code.claude.com/docs/en/authentication)
- [code.claude.com — Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)
- [code.claude.com — Run prompts on a schedule](https://code.claude.com/docs/en/scheduled-tasks)
- [code.claude.com — Run Claude Code programmatically (headless)](https://code.claude.com/docs/en/headless)
- [code.claude.com — CLI reference](https://code.claude.com/docs/en/cli-reference)
- [code.claude.com — Model configuration](https://code.claude.com/docs/en/model-config)
- [code.claude.com — Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
- [anthropic.com — Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms) (effective 2025-10-08)
- [anthropic.com — Usage Policy](https://www.anthropic.com/legal/aup) (effective 2025-09-15)
- Local: `claude --help`, `claude --version` (2.1.283), and one live `claude -p` smoke-test invocation (2026-09-27)

**OpenAI / Codex CLI:**
- [help.openai.com — Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [help.openai.com — How banked Codex resets work](https://help.openai.com/en/articles/20001498-how-banked-codex-resets-work)
- [help.openai.com — Paid Work and Codex rate limit resets](https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets)
- [help.openai.com — Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card)
- [help.openai.com — OpenAI Account Sharing Policy](https://help.openai.com/en/articles/10471989-openai-account-sharing-policy)
- [learn.chatgpt.com — Pricing](https://learn.chatgpt.com/docs/pricing)
- [learn.chatgpt.com — Models](https://learn.chatgpt.com/docs/models)
- [learn.chatgpt.com — Auth](https://learn.chatgpt.com/docs/auth)
- [learn.chatgpt.com — Developer commands](https://learn.chatgpt.com/docs/developer-commands)
- [learn.chatgpt.com — Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [learn.chatgpt.com — Codex config basics](https://learn.chatgpt.com/codex/config-file/config-basic)
- [learn.chatgpt.com — Codex config reference](https://learn.chatgpt.com/codex/config-file/config-reference)
- [learn.chatgpt.com — Codex AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md)
- [openai.com — Terms of Use](https://openai.com/policies/row-terms-of-use/) (effective 2026-01-01)
- [openai.com — Usage Policies](https://openai.com/policies/usage-policies/)
- Local: `codex --help`, `codex exec --help`, `codex mcp --help`, `codex --version` (0.157.1), `~/.codex/config.toml`, and one live `codex exec` smoke-test invocation (2026-09-27)

**This repo's sibling project (primary source for in-house prior art):**
- `/home/varigg/code/adventure-library/src/adventure_library/llm/claude_cli.py`
- `/home/varigg/code/adventure-library/src/adventure_library/llm/provider.py`
- `/home/varigg/code/adventure-library/docs/architecture/jobs.md`
- `/home/varigg/code/adventure-library/docs/adr/000-legacy-decision-log.md` (decision 5)
- `/home/varigg/code/adventure-library/docs/adr/042-big-document-reuse-index-pages-only.md`
