"""Deploy probe: the installed release answers on the web and over MCP.

    probe.py <bookmarks-executable>

Run with the installed tool's own Python, so it exercises the deployed
environment. Read-only: the console renders the store, the capture route
rejects an empty payload (422, nothing saved), and the MCP server, spawned
over stdio like Claude Code does, answers `search` and `status`. A search
embeds the query through Ollama; no `claude -p` call is made.
"""

import asyncio
import json
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from bookmarks.settings import Settings

STARTUP_SECONDS = 30


def probe_web(base: str) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while True:
        try:
            console = httpx.get(f"{base}/", timeout=5)
            break
        except httpx.TransportError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)
    assert console.status_code == 200, f"GET / answered {console.status_code}"
    capture = httpx.post(f"{base}/api/items", json={}, timeout=5)
    assert capture.status_code == 422, (
        f"POST /api/items {{}} answered {capture.status_code}"
    )


async def probe_mcp(executable: str) -> None:
    server = StdioServerParameters(command=executable, args=["mcp"])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as s:
        await s.initialize()
        for tool, arguments in (
            ("search", {"query": "probe", "limit": 1}),
            ("status", {}),
        ):
            result = await s.call_tool(tool, arguments)
            assert not result.is_error, f"{tool}: {result.content[0].text}"
        status = json.loads(result.content[0].text)
        assert "items" in status, "status lacks an item count"


def main() -> None:
    executable = sys.argv[1]
    settings = Settings.from_env()
    probe_web(f"http://127.0.0.1:{settings.port}")
    print("probe: web ok", file=sys.stderr)
    asyncio.run(probe_mcp(executable))
    print("probe: mcp ok", file=sys.stderr)


if __name__ == "__main__":
    main()
