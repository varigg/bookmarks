"""Command-line entry points; each command is a composition root."""

import argparse
from collections.abc import Iterator
from contextlib import contextmanager

from bookmarks import db
from bookmarks.clock import SystemClock
from bookmarks.service import Bookmarks
from bookmarks.settings import Settings


def _service_opener(settings: Settings):
    @contextmanager
    def open_service() -> Iterator[Bookmarks]:
        conn = db.connect(settings.db_path)
        try:
            yield Bookmarks(conn, clock=SystemClock(), settings=settings)
        finally:
            conn.close()

    return open_service


def _serve(settings: Settings, args: argparse.Namespace) -> None:
    import uvicorn

    from bookmarks.web.app import create_app

    uvicorn.run(
        create_app(_service_opener(settings)), host=settings.host, port=settings.port
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bookmarks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="run the web server (capture API)").set_defaults(
        handler=_serve
    )
    args = parser.parse_args(argv)
    args.handler(Settings.from_env(), args)


if __name__ == "__main__":
    main()
