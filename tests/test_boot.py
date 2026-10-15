"""Boot check (AGENTS.md gate 1): every module imports and both servers build.

Catches an import broken by a code move, which only fails when the module loads.
"""

import asyncio
import importlib
import pkgutil
import subprocess
import sys
from pathlib import Path

import bookmarks
from bookmarks.mcp_server import build_server
from bookmarks.web.app import create_app


def test_every_module_imports():
    for module in pkgutil.walk_packages(bookmarks.__path__, "bookmarks."):
        importlib.import_module(module.name)


def test_web_app_registers_capture_route(open_service):
    paths = {route.path for route in create_app(open_service).routes}
    assert "/api/items" in paths


def test_mcp_server_registers_search_tool(open_service):
    tools = asyncio.run(build_server(open_service).list_tools())
    assert "search" in {tool.name for tool in tools}


def test_cli_help_runs():
    cli = Path(sys.executable).parent / "bookmarks"
    result = subprocess.run([cli, "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "usage: bookmarks" in result.stdout
