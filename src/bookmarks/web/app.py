"""FastAPI app: the capture API (and later the web console).

The app holds no behaviour: it validates payloads, calls the core and
translates the result.
"""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bookmarks.service import Bookmarks
from bookmarks.urls import InvalidUrl

OpenService = Callable[[], AbstractContextManager[Bookmarks]]


class CapturePayload(BaseModel):
    url: str
    html: str | None = None
    title: str | None = None
    note: str | None = None


def create_app(open_service: OpenService) -> FastAPI:
    app = FastAPI(title="bookmarks")

    def service() -> Iterator[Bookmarks]:
        with open_service() as svc:
            yield svc

    @app.post("/api/items")
    def capture(payload: CapturePayload, svc: Annotated[Bookmarks, Depends(service)]):
        try:
            result = svc.save(
                payload.url, html=payload.html, title=payload.title, note=payload.note
            )
        except InvalidUrl as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(
            status_code=200 if result.outcome == "already_saved" else 201,
            content={
                "outcome": result.outcome,
                "message": result.message,
                "note_added": result.note_added,
                "item": {
                    "id": result.item.id,
                    "url": result.item.url,
                    "status": result.item.status,
                    "saved_at": result.item.saved_at,
                },
            },
        )

    return app
