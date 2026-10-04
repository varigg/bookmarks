# Retrieve source text in code, not through the summarising agent

The summarising stage could let `claude -p` fetch pages itself with its WebFetch tool, which would delete most of the retrieving code. We keep retrieving as its own stage, in code, running on thunderbird, and the summariser call stays tool-free: it receives the source text in its prompt and nothing else.

## Considered Options

- **Agent fetches with WebFetch.** Rejected because:
  - WebFetch requests come from Anthropic's IP ranges, and some sites block them; a fetch from thunderbird uses our own address.
  - WebFetch hands the agent a model's processed reading of the page rather than the page text, so the summary would be written from a summary.
  - Page text is untrusted. With a tool available, a hostile page could steer the agent into fetching other URLs from thunderbird's network; tool-free, it can only influence the JSON reply, which is schema-validated.
  - It would make every summary a multi-turn call with tool output in context, spending the `claude -p` budget the drain exists to protect.
  - The rendered HTML a capture surface sends (login-walled and JavaScript-built pages) would still have to reach the prompt, so retrieving code would not disappear anyway.
- **Retrieving in code, inside the summarising step.** The previous shape. Superseded by making retrieving a stage of its own, so that fetch failures (blocked, not found, timed out) are handled without spending LLM budget and source text is kept only until the item is summarised.

## Consequences

- Retrieval failures are classified from HTTP results, deterministically, and lifecycle policy decides what each one means.
- `bookmarks retrieve <url>` (#39) prints exactly the source text the pipeline would send, and is the tool to use instead of WebFetch when debugging what a page yields.
