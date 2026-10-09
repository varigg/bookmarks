"""FastAPI app: the capture API and the web console.

The app holds no behaviour: it validates payloads, calls the core and
translates the result.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from bookmarks import store
from bookmarks.search import Filters
from bookmarks.service import Bookmarks, OpenService
from bookmarks.store import InvalidUrl

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


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
                    "url": result.url,
                    "status": result.status,
                    "saved_at": result.saved_at,
                },
            },
        )

    @app.get("/")
    def index(
        request: Request,
        svc: Annotated[Bookmarks, Depends(service)],
        q: str = "",
        type: str = "",
        domain: str = "",
    ):
        filters = Filters(types=[type] if type else (), domain=domain or None)
        if q.strip():
            result = svc.search(q, filters)
            items, notes = [hit.item for hit in result.hits], result.notes
        else:
            items, notes = svc.list_items(filters=filters), []
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "items": items,
                "notes": notes,
                "status": svc.status(),
                "types": svc.list_types(),
                "lede": store.lede,
                "q": q,
                "type": type,
                "domain": domain,
            },
        )

    @app.get("/items/{item_id}")
    def item_detail(
        request: Request, item_id: int, svc: Annotated[Bookmarks, Depends(service)]
    ):
        item = svc.find_item(item_id=item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such item")
        return templates.TemplateResponse(
            request,
            "item.html",
            {"item": item, "archive_url": store.archive_url(item.url)},
        )

    @app.post("/items/{item_id}/delete")
    def delete(item_id: int, svc: Annotated[Bookmarks, Depends(service)]):
        if svc.delete_item(item_id=item_id) is None:
            raise HTTPException(status_code=404, detail="no such item")
        return RedirectResponse("/", status_code=303)

    return app
