"""Claude Code CLI adapter: claude -p in single-turn JSON mode.

Copied and adapted from adventure-library `src/adventure_library/llm/claude_cli.py`
at commit b264b17."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from bookmarks.llm.provider import LLMRequest, LLMResult, ProviderFailure

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
            str(request.max_turns),
            "--system-prompt",
            request.system_prompt,
        ]
        if request.single_turn:
            # An explicit empty string is Claude CLI's documented sentinel for
            # disabling every built-in tool. Omitting --tools leaves the
            # default tool set reachable.
            cmd += ["--tools", ""]
        elif request.tools:
            # --tools restricts the built-in toolset; --allowedTools only
            # auto-approves and leaves every other tool reachable.
            cmd += ["--tools", *request.tools]
        for directory in request.add_dirs:
            cmd += ["--add-dir", directory]
        # --strict-mcp-config alone (with no --mcp-config) loads zero MCP
        # servers, on every call the provider builds (#140) — a bare
        # `claude -p` otherwise loads whatever MCP servers the caller's
        # ~/.claude.json registers, measured at ~30K tokens of tool
        # definitions per call. Passing --mcp-config "{}" used to be
        # belt-and-suspenders but newer CLI versions reject an empty object
        # as invalid (it wants a top-level mcpServers key).
        cmd += ["--strict-mcp-config"]
        model = request.model or self.model
        if model:
            cmd += ["--model", model]
        timeout = request.timeout if request.timeout is not None else self.timeout
        run_dir = Path(tempfile.mkdtemp(prefix="bookmarks-claude-"))
        try:
            try:
                run_kwargs = {
                    "input": request.user_prompt,
                    "capture_output": True,
                    "text": True,
                    "timeout": timeout,
                    "cwd": run_dir,
                }
                if request.single_turn:
                    env = os.environ.copy()
                    env.pop("CLAUDECODE", None)
                    run_kwargs["env"] = env
                proc = subprocess.run(cmd, **run_kwargs)
            except subprocess.TimeoutExpired:
                raise ProviderFailure(
                    "timeout", f"claude -p exceeded {timeout}s", retryable=True
                ) from None
            except FileNotFoundError:
                raise ProviderFailure(
                    "unavailable", f"{self.executable} not installed", retryable=False
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
                # Deliberately retain this path's broader retry rule: unlike
                # _normalize's zero-exit is_error path, non-zero exits retry
                # invalid_output as well.
                raise ProviderFailure(
                    failure_class,
                    f"claude -p exit {proc.returncode}; "
                    f"stderr: {_excerpt(proc.stderr)}; "
                    f"stdout: {stdout_message}",
                    retryable=failure_class in ("transient", "invalid_output"),
                    raw=json.dumps(
                        {
                            "returncode": proc.returncode,
                            "stdout": proc.stdout,
                            "stderr": proc.stderr,
                        }
                    ),
                    num_turns=envelope.get("num_turns")
                    if envelope is not None
                    else None,
                )
            return self._normalize(proc.stdout)
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def _normalize(self, stdout: str) -> LLMResult:
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            raise ProviderFailure(
                "invalid_output",
                f"unparseable CLI output: {_excerpt(stdout, 200)}",
                retryable=True,
                raw=stdout,
            ) from None
        if not isinstance(envelope, dict):
            raise ProviderFailure(
                "invalid_output",
                f"expected JSON object envelope, got: {_excerpt(stdout, 200)}",
                retryable=True,
                raw=stdout,
            )
        result_text = str(envelope.get("result", ""))
        if envelope.get("subtype") == "error_max_turns":
            raise ProviderFailure(
                "invalid_output",
                result_text[:_EXCERPT_LIMIT]
                or "claude exhausted the maximum number of turns",
                retryable=True,
                raw=stdout,
                num_turns=envelope.get("num_turns"),
            )
        if envelope.get("is_error"):
            # Classify the whole envelope, not just result: an empty result
            # field must not blind the rate-limit/auth pause detection, and
            # the message must name the subtype the CLI reported.
            failure_class = self._classify(stdout)
            raise ProviderFailure(
                failure_class,
                _summarize_envelope(envelope),
                retryable=failure_class == "transient",
                raw=stdout,
                num_turns=envelope.get("num_turns"),
            )
        return LLMResult(
            text=result_text,
            model=envelope.get("model") or self.model or "unknown",
            raw=stdout,
            num_turns=envelope.get("num_turns"),
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
