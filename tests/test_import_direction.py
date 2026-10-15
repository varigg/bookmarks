"""Import rules: ADR 0002 (the store never imports ingestion; only the
composition roots and service.py, until it splits (#42), may) and AGENTS.md
(core modules never import transport libraries)."""

import ast
from pathlib import Path

import bookmarks

PKG = Path(bookmarks.__file__).parent
ALLOWED = {"cli.py", "web/app.py", "mcp_server.py", "service.py"}


def _imports(tree: ast.Module) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names += [f"{node.module}.{a.name}" for a in node.names]
    return names


def test_only_composition_roots_import_ingest():
    offenders = []
    for path in PKG.rglob("*.py"):
        rel = path.relative_to(PKG).as_posix()
        if rel.startswith("ingest/") or rel in ALLOWED:
            continue
        for name in _imports(ast.parse(path.read_text())):
            if name == "bookmarks.ingest" or name.startswith("bookmarks.ingest."):
                offenders.append(f"{rel}: {name}")
    assert offenders == []


# AGENTS.md: core modules never import these; outside systems arrive as a
# Protocol from a composition root. These files are the transport adapters
# (web/app.py, mcp_server.py, cli.py) and the edges that implement a Protocol.
TRANSPORT = ("fastapi", "mcp", "httpx", "subprocess")
ADAPTERS = {
    "cli.py",
    "web/app.py",
    "mcp_server.py",
    "msmtp.py",
    "ollama.py",
    "ingest/httpx_fetcher.py",
    "ingest/llm/claude_cli.py",
}


def test_core_modules_do_not_import_transport():
    offenders = []
    for path in PKG.rglob("*.py"):
        rel = path.relative_to(PKG).as_posix()
        if rel in ADAPTERS:
            continue
        for name in _imports(ast.parse(path.read_text())):
            if name.split(".")[0] in TRANSPORT:
                offenders.append(f"{rel}: {name}")
    assert offenders == []
