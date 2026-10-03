"""Claude CLI adapter over recorded outputs.

Copied and adapted from adventure-library `tests/test_claude_cli.py` at
commit b264b17."""

import json
import subprocess

import pytest

from bookmarks.llm.claude_cli import _EXCERPT_LIMIT, ClaudeCodeCLIProvider
from bookmarks.llm.provider import LLMRequest, ProviderFailure

REQUEST = LLMRequest(
    system_prompt="Return only JSON.",
    user_prompt="extract stuff",
)


def _completed(stdout: str = "", returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_submit_success(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": '{"title": "X"}',
            "model": "claude-sonnet-5",
            "num_turns": 7,
        }
    )
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        captured["cwd"] = kwargs.get("cwd")
        return _completed(stdout=envelope)

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = ClaudeCodeCLIProvider()
    result = provider.submit(REQUEST)
    assert result.text == '{"title": "X"}'
    assert result.model == "claude-sonnet-5"
    assert result.num_turns == 7
    assert captured["input"] == "extract stuff"
    assert "-p" in captured["cmd"] and "--max-turns" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--max-turns") + 1] == "1"
    assert captured["cwd"]


def test_submit_success_without_num_turns_field_is_none(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "{}",
            "model": "claude-sonnet-5",
        }
    )
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout=envelope)
    )
    result = ClaudeCodeCLIProvider().submit(REQUEST)
    assert result.num_turns is None


def test_submit_applies_per_request_turns_and_timeout(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "{}",
            "model": "claude-sonnet-5",
        }
    )
    request = LLMRequest(
        system_prompt="Return only JSON.",
        user_prompt="Read the artifact.",
        max_turns=60,
        timeout=900,
    )
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured.update(kwargs)
        return _completed(stdout=envelope)

    monkeypatch.setattr(subprocess, "run", fake_run)
    ClaudeCodeCLIProvider(timeout=300).submit(request)

    cmd = captured["cmd"]
    assert cmd[cmd.index("--max-turns") + 1] == "60"
    assert captured["timeout"] == 900


def test_submit_timeout(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider(timeout=1).submit(REQUEST)
    assert excinfo.value.failure_class == "timeout"


@pytest.mark.parametrize(
    "stderr,expected",
    [
        ("Error: not logged in. Run /login", "auth"),
        ("API rate limit exceeded", "rate_limit"),
        ("Opus limit reached", "rate_limit"),
        ("5-hour session limit reached", "rate_limit"),
        ("weekly limit reached", "rate_limit"),
        ("segfault or whatever", "transient"),
    ],
)
def test_submit_classifies_cli_errors(monkeypatch, stderr, expected):
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(returncode=1, stderr=stderr)
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == expected


def test_submit_nonzero_exit_reports_both_streams_and_exit_code(monkeypatch):
    # Regression for 2026-07-28: the CLI put the limit error on stdout with an
    # empty stderr, and the stderr-only message left 29 jobs failed with no
    # diagnostic and no pause.
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: _completed(
            returncode=1, stdout="Claude AI usage limit reached|1753690210"
        ),
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "rate_limit"
    message = str(excinfo.value)
    assert "exit 1" in message
    assert "usage limit reached" in message


def test_submit_nonzero_exit_empty_streams_says_so(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _completed(returncode=143))
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "transient"
    message = str(excinfo.value)
    assert "exit 143" in message
    assert "stderr: (empty)" in message
    assert "stdout: (empty)" in message


def test_submit_rejects_garbled_stdout(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout="not json at all")
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "invalid_output"


def test_submit_rejects_non_object_json_envelope(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _completed(stdout="null"))
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "invalid_output"


def test_submit_classifies_max_turns_as_invalid_output(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "subtype": "error_max_turns",
            "is_error": True,
            "result": "maximum turns reached",
            "num_turns": 60,
        }
    )
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout=envelope)
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "invalid_output"


def test_submit_missing_binary(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "unavailable"
    assert "not installed" in str(excinfo.value)


def test_submit_error_envelope(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "is_error": True,
            "result": "Usage limit reached",
            "num_turns": 3,
        }
    )
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout=envelope)
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "rate_limit"


def test_submit_error_envelope_with_empty_result_names_subtype(monkeypatch):
    envelope = json.dumps(
        {
            "type": "result",
            "subtype": "error_during_execution",
            "is_error": True,
            "result": "",
        }
    )
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout=envelope)
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "transient"
    message = str(excinfo.value)
    assert "error_during_execution" in message
    assert "result: (empty)" in message


def test_submit_error_envelope_classifies_from_whole_envelope(monkeypatch):
    # The pause-worthy marker sits outside the result field; classification
    # must still see it.
    envelope = json.dumps(
        {
            "type": "result",
            "is_error": True,
            "result": "",
            "error": "usage limit reached",
        }
    )
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _completed(stdout=envelope)
    )
    with pytest.raises(ProviderFailure) as excinfo:
        ClaudeCodeCLIProvider().submit(REQUEST)
    assert excinfo.value.failure_class == "rate_limit"


def _nonzero_envelope(result: str, subtype: str = "error_during_execution") -> str:
    """An is_error envelope in the CLI's real field order, where the zeroed
    usage/modelUsage boilerplate precedes `result`. Reproduces the shape that
    left job 162's stored message truncated mid-boilerplate on 2026-07-31."""
    return json.dumps(
        {
            "type": "result",
            "subtype": subtype,
            "is_error": True,
            "duration_api_ms": 0,
            "duration_ms": 0,
            "num_turns": 1,
            "stop_reason": "stop_sequence",
            "session_id": "3b0878bc-ec75-4308-91b5-8fd1f2fa9791",
            "uuid": "b5ec6ed3-376d-4292-89fe-8bb216bb96b6",
            "total_cost_usd": 0,
            "usage": {
                "input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
                "server_tool_use": {
                    "web_search_requests": 0,
                    "web_fetch_requests": 0,
                },
                "service_tier": "standard",
                "cache_creation": {
                    "ephemeral_1h_input_tokens": 0,
                    "ephemeral_5m_input_tokens": 0,
                },
                "inference_geo": "",
                "iterations": [],
                "speed": "standard",
            },
            "modelUsage": {},
            "permission_denials": [],
            "result": result,
        }
    )


def _submit_nonzero(monkeypatch, stdout: str, stderr: str = ""):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kw: _completed(returncode=1, stdout=stdout, stderr=stderr),
    )
    return ClaudeCodeCLIProvider().submit(REQUEST)


def test_submit_nonzero_exit_with_envelope_reports_subtype_and_result(monkeypatch):
    """The load-bearing regression: `claude -p` exits non-zero AND prints a JSON
    envelope, so the envelope must be parsed rather than sliced."""
    explanation = "the model refused to continue: unrecoverable tool loop"
    envelope = _nonzero_envelope(explanation)
    # Guard the fixture: if the `result` KEY no longer sits past the excerpt
    # limit this test would pass without ever exercising the defect. Match on
    # the trailing colon — bare '"result"' also matches the `type` field's
    # value at the head of the envelope.
    assert envelope.index('"result":') > _EXCERPT_LIMIT

    with pytest.raises(ProviderFailure) as excinfo:
        _submit_nonzero(monkeypatch, envelope)

    message = str(excinfo.value)
    assert explanation in message
    assert "error_during_execution" in message
    assert "exit 1" in message


def test_submit_nonzero_exit_envelope_empty_result_still_says_empty(monkeypatch):
    with pytest.raises(ProviderFailure) as excinfo:
        _submit_nonzero(monkeypatch, _nonzero_envelope(""))
    message = str(excinfo.value)
    assert "result: (empty)" in message
    assert "error_during_execution" in message
    assert "exit 1" in message


def test_submit_nonzero_exit_envelope_keeps_stderr_visible(monkeypatch):
    """stderr can carry the real cause (a wrapper or shell error) the envelope
    never mentions, so parsing stdout must not hide it."""
    with pytest.raises(ProviderFailure) as excinfo:
        _submit_nonzero(
            monkeypatch,
            _nonzero_envelope("inner explanation"),
            stderr="ulimit killed it",
        )
    message = str(excinfo.value)
    assert "ulimit killed it" in message
    assert "inner explanation" in message


@pytest.mark.parametrize("stdout", ['["a", "b"]'])
def test_submit_nonzero_exit_non_object_json_falls_back(monkeypatch, stdout):
    """Valid JSON that is not an object carries no envelope semantics; the
    raw-excerpt message is the correct fallback (mirrors _normalize's guard)."""
    with pytest.raises(ProviderFailure) as excinfo:
        _submit_nonzero(monkeypatch, stdout)
    message = str(excinfo.value)
    assert "exit 1" in message
    assert f"stdout: {stdout}" in message


def test_submit_nonzero_exit_max_turns_envelope_is_invalid_output(monkeypatch):
    with pytest.raises(ProviderFailure) as excinfo:
        _submit_nonzero(
            monkeypatch, _nonzero_envelope("ran out", subtype="error_max_turns")
        )
    assert excinfo.value.failure_class == "invalid_output"


# --- the call shape -----------------------------------------------------------
#
# The summariser call is bounded, tool-free and isolated: it reads untrusted
# page text. This pins the exact CLI invocation shape and env handling.


def _envelope(result: str = "{}", num_turns: int = 1) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": result,
            "model": "claude-sonnet-5",
            "num_turns": num_turns,
        }
    )


def test_single_turn_mode_isolates_the_call(monkeypatch):
    """Every call must: restrict to zero tools (`--tools ""`, per `claude
    --help`'s documented sentinel — a bare omitted --tools leaves every default
    tool reachable, which is wrong for an unattended, untrusted-input call),
    isolate MCP (`--strict-mcp-config` alone, no `--mcp-config` — an empty
    `--mcp-config {}` is rejected as invalid by newer CLI versions), cap at one turn,
    take its model from the per-request override (not the provider's own
    constructor default), send the prompt on stdin, and unset CLAUDECODE (the
    nested-session marker) from the child's environment so a `claude -p`
    shelled out from *inside* a Claude Code session — this worker's own
    intended deployment — does not see itself as nested. Every other inherited
    env var (a stand-in for the whole ambient environment) must survive
    untouched: this is a targeted removal, not an `env={}` wipe.
    """
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("SOME_OTHER_VAR", "keep-me")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        captured["env"] = kwargs.get("env")
        return _completed(stdout=_envelope())

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = ClaudeCodeCLIProvider(model="opus")  # provider default must lose
    request = LLMRequest(
        system_prompt="Summarise the page as JSON.",
        user_prompt="summarise this page",
        max_turns=1,
        model="sonnet",
    )

    result = provider.submit(request)

    assert result.text == "{}"
    cmd = captured["cmd"]

    def _arg_after(flag):
        return cmd[cmd.index(flag) + 1]

    assert _arg_after("--tools") == ""
    assert "--strict-mcp-config" in cmd
    assert "--mcp-config" not in cmd
    assert _arg_after("--max-turns") == "1"
    assert _arg_after("--model") == "sonnet"  # per-request override wins
    assert captured["input"] == "summarise this page"

    env = captured["env"]
    assert env is not None, "the call must pass an explicit env, not inherit"
    assert "CLAUDECODE" not in env
    assert env.get("SOME_OTHER_VAR") == "keep-me"
