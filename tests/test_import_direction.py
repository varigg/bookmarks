"""ADR 0002: the store never imports ingestion. Only the composition roots and
service.py (until it splits, #42) may reach into bookmarks.ingest."""

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
