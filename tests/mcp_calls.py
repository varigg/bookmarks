"""Calling MCP tools in tests."""

import asyncio
import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError


def called(server, tool: str, **arguments) -> dict:
    """Call `tool` expecting success; return its JSON result."""
    content = asyncio.run(server.call_tool(tool, arguments))
    return json.loads(content.content[0].text)


def refused(server, tool: str, arguments: dict) -> str:
    """Call `tool` expecting a refusal the agent can read; a crash fails the test.

    mcp 2 reports any exception but ToolError as a crash and hides its message.
    """
    with pytest.raises(ToolError) as raised:
        asyncio.run(server.call_tool(tool, arguments))
    assert not isinstance(raised.value, UnexpectedToolError), raised.value.__cause__
    return str(raised.value)
