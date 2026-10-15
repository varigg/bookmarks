"""Shape test (AGENTS.md gate 4): transport stays thin.

A FastAPI handler or MCP tool validates, calls an owner and translates; past
MAX_LINES it is doing business logic. Docstrings do not count: an MCP tool's
docstring is its contract. Import rules live in test_import_direction.py.
"""

import ast
from pathlib import Path

import bookmarks

PKG = Path(bookmarks.__file__).parent
TRANSPORT_FILES = ("web/app.py", "mcp_server.py")
REGISTRARS = {"app", "mcp"}  # the FastAPI app and FastMCP server names
MAX_LINES = 25


def _is_handler(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(d, ast.Call)
        and isinstance(d.func, ast.Attribute)
        and isinstance(d.func.value, ast.Name)
        and d.func.value.id in REGISTRARS
        for d in fn.decorator_list
    )


def _code_lines(fn: ast.FunctionDef) -> int:
    body = fn.body
    if ast.get_docstring(fn) is not None and len(body) > 1:
        body = body[1:]
    return fn.end_lineno - body[0].lineno + 1


def test_handlers_and_tools_stay_short():
    handlers, offenders = 0, []
    for rel in TRANSPORT_FILES:
        for node in ast.walk(ast.parse((PKG / rel).read_text())):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _is_handler(
                node
            ):
                handlers += 1
                if (n := _code_lines(node)) > MAX_LINES:
                    offenders.append(f"{rel}:{node.lineno} {node.name} ({n} lines)")
    assert handlers > 0, "no handlers found; the decorator match is stale"
    assert offenders == []
