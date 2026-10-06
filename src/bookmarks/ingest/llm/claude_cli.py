"""Claude Code CLI adapter: claude -p in single-turn JSON mode.

Copied and adapted from adventure-library `src/adventure_library/llm/claude_cli.py`
at commit b264b17."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from bookmarks.ingest.llm.provider import LLMRequest, LLMResult, ProviderFailure

_AUTH_MARKERS = ("not logged in", "authentication", "/login", "unauthorized")
_EXCERPT_LIMIT = 500


def _excerpt(text: str, limit: int = _EXCERPT_LIMIT) -> str:
    """Bounded, never-empty slice for failure messages: an empty stream must
    say so explicitly, or the resulting message is indistinguishable from a
    logging bug."""
    text = text.strip()
    return text[:limit] if text else "(empty)"


def _summarize_envelope(envelope: dict) -> str:
    """The bounded failure summary both failure paths report, so a parsed
    envelope reads the same whether the CLI exited zero or not."""
    result_text = str(envelope.get("result", ""))
    return (
        f"is_error envelope (subtype: {envelope.get('subtype')!r}); "
        f"result: {_excerpt(result_text)}"
    )


def _try_parse_envelope(stdout: str) -> dict | None:
    """Parse stdout when it is a JSON object envelope, else return None.

    Never raises: the CLI is free to write anything to stdout on the way out.
    """
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return envelope if isinstance(envelope, dict) else None


_RATE_MARKERS = (
    "rate limit",
    "usage limit",
    "overloaded",
    "quota",
    "limit reached",
)


class ClaudeCodeCLIProvider:
    name = "claude-cli"

    def __init__(
        self, executable: str = "claude", model: str | None = None, timeout: int = 300
    ):
        self.executable = executable
        self.model = model
        self.timeout = timeout

    def submit(self, request: LLMRequest) -> LLMResult:
        cmd = [
            self.executable,
            "-p",
            "--output-format",
            "json",
            "--max-turns",
            "1",
            "--system-prompt",
            request.system_prompt,
            # An explicit empty string is Claude CLI's documented sentinel for
            # disabling every built-in tool. Omitting --tools leaves the
            # default tool set reachable.
            "--tools",
            "",
        ]
        # --strict-mcp-config alone (with no --mcp-config) loads zero MCP
        # servers, on every call the provider builds (#140) — a bare
        # `claude -p` otherwise loads whatever MCP servers the caller's
        # ~/.claude.json registers, measured at ~30K tokens of tool
        # definitions per call. Passing --mcp-config "{}" used to be
        # belt-and-suspenders but newer CLI versions reject an empty object
        # as invalid (it wants a top-level mcpServers key).
        cmd += ["--strict-mcp-config"]
        if self.model:
            cmd += ["--model", self.model]
        run_dir = Path(tempfile.mkdtemp(prefix="bookmarks-claude-"))
        try:
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            try:
                proc = subprocess.run(
                    cmd,
                    input=request.user_prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=run_dir,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                raise ProviderFailure(
                    "timeout", f"claude -p exceeded {self.timeout}s"
                ) from None
            except FileNotFoundError:
                raise ProviderFailure(
                    "unavailable", f"{self.executable} not installed"
                ) from None
            if proc.returncode != 0:
                # The CLI reports errors on either stream (--output-format json
                # tends to use stdout), so message and classification must both
                # see all the evidence — a stderr-only message came up empty
                # for a whole night of failures once.
                failure_class = self._classify(proc.stderr + "\n" + proc.stdout)
                envelope = _try_parse_envelope(proc.stdout)
                stdout_message = (
                    _summarize_envelope(envelope)
                    if envelope is not None
                    else _excerpt(proc.stdout)
                )
                raise ProviderFailure(
                    failure_class,
                    f"claude -p exit {proc.returncode}; "
                    f"stderr: {_excerpt(proc.stderr)}; "
                    f"stdout: {stdout_message}",
                )
            return self._normalize(proc.stdout)
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def _normalize(self, stdout: str) -> LLMResult:
        envelope = _try_parse_envelope(stdout)
        if envelope is None:
            # The message says which it was: not JSON, or JSON but no object.
            try:
                json.loads(stdout)
            except json.JSONDecodeError:
                raise ProviderFailure(
                    "invalid_output",
                    f"unparseable CLI output: {_excerpt(stdout, 200)}",
                ) from None
            raise ProviderFailure(
                "invalid_output",
                f"expected JSON object envelope, got: {_excerpt(stdout, 200)}",
            )
        result_text = str(envelope.get("result", ""))
        if envelope.get("subtype") == "error_max_turns":
            raise ProviderFailure(
                "invalid_output",
                result_text[:_EXCERPT_LIMIT]
                or "claude exhausted the maximum number of turns",
            )
        if envelope.get("is_error"):
            # Classify the whole envelope, not just result: an empty result
            # field must not blind the rate-limit/auth pause detection, and
            # the message must name the subtype the CLI reported.
            raise ProviderFailure(self._classify(stdout), _summarize_envelope(envelope))
        return LLMResult(
            text=result_text,
            model=envelope.get("model") or self.model or "unknown",
        )

    @staticmethod
    def _classify(output: str) -> str:
        lowered = output.lower()
        if "error_max_turns" in lowered or "max turns" in lowered:
            return "invalid_output"
        if any(marker in lowered for marker in _AUTH_MARKERS):
            return "auth"
        if any(marker in lowered for marker in _RATE_MARKERS):
            return "rate_limit"
        return "transient"
