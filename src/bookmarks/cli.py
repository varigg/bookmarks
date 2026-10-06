"""Command-line entry points; each command is a composition root."""

import argparse
from collections.abc import Iterator
from contextlib import contextmanager

from bookmarks import db
from bookmarks.clock import SystemClock
from bookmarks.embed import OllamaEmbedder
from bookmarks.ingest.fetch import HttpxFetcher
from bookmarks.ingest.llm.claude_cli import ClaudeCodeCLIProvider
from bookmarks.service import Bookmarks
from bookmarks.settings import Settings


def _service_opener(settings: Settings):
    @contextmanager
    def open_service() -> Iterator[Bookmarks]:
        conn = db.connect(settings.db_path)
        try:
            yield Bookmarks(
                conn,
                clock=SystemClock(),
                settings=settings,
                fetcher=HttpxFetcher(timeout=settings.fetch_timeout),
                summariser=ClaudeCodeCLIProvider(
                    executable=settings.claude_executable,
                    model=settings.summariser_model,
                    timeout=settings.summariser_timeout,
                ),
                embedder=OllamaEmbedder(
                    settings.embed_model,
                    settings.ollama_url,
                    timeout=settings.embed_timeout,
                ),
            )
        finally:
            conn.close()

    return open_service


def _serve(settings: Settings, args: argparse.Namespace) -> None:
    import uvicorn

    from bookmarks.web.app import create_app

    uvicorn.run(
        create_app(_service_opener(settings)), host=settings.host, port=settings.port
    )


def _drain(settings: Settings, args: argparse.Namespace) -> None:
    with _service_opener(settings)() as svc:
        report = svc.drain(limit=args.limit)
    print(
        f"drain: {report.summarised} summarised, {report.failed} failed, "
        f"{report.retry} to retry"
        + (f"; stopped: {report.stopped}" if report.stopped else "")
    )


def _embed(settings: Settings, args: argparse.Namespace) -> None:
    with _service_opener(settings)() as svc:
        report = svc.embed()
    print(
        f"embed: {report.embedded} embedded"
        + (f"; stopped: {report.error}" if report.error else "")
    )
    if report.error:
        raise SystemExit(1)


def _mcp(settings: Settings, args: argparse.Namespace) -> None:
    from bookmarks.mcp_server import build_server

    build_server(_service_opener(settings)).run()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bookmarks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="run the web server (capture API)").set_defaults(
        handler=_serve
    )
    drain = commands.add_parser("drain", help="summarise pending submissions")
    drain.add_argument("--limit", type=int, default=None)
    drain.set_defaults(handler=_drain)
    commands.add_parser(
        "embed", help="embed summarised items lacking a vector"
    ).set_defaults(handler=_embed)
    commands.add_parser("mcp", help="run the MCP server over stdio").set_defaults(
        handler=_mcp
    )
    args = parser.parse_args(argv)
    args.handler(Settings.from_env(), args)


if __name__ == "__main__":
    main()
