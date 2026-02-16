from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from .config import Settings, load_settings
from .db import connect, init_db
from .markdown import MarkdownRenderer
from .repo import (
    create_note,
    delete_note,
    export_all,
    get_note,
    list_notes,
    list_tags,
    parse_tags,
    search_notes,
    toggle_pin,
    update_note,
)
from .schemas import NoteListItem, NoteOut


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    base_dir = Path(__file__).parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    static_dir = base_dir / "static"
    md = MarkdownRenderer()

    security = HTTPBasic(auto_error=False)

    def require_auth(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
        if not settings.auth_enabled:
            return None
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if credentials.username != settings.auth_user or credentials.password != settings.auth_pass:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return None

    app = FastAPI(
        title="MintMemo",
        version="0.1.0",
        dependencies=[Depends(require_auth)],
    )

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.on_event("startup")
    def _startup() -> None:
        with connect(settings.db_path) as conn:
            init_db(conn)

    def _is_htmx(request: Request) -> bool:
        return request.headers.get("HX-Request", "").lower() == "true"

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, tag: str | None = None) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            notes = list_notes(conn, tag=tag)
            tags = list_tags(conn)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "notes": notes, "tags": tags, "active_tag": tag},
        )

    @app.get("/tags", response_class=HTMLResponse)
    def tags_page(request: Request) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            tags = list_tags(conn)
        return templates.TemplateResponse("tags.html", {"request": request, "tags": tags})

    @app.get("/search", response_class=HTMLResponse)
    def search_page(request: Request, q: str | None = None) -> HTMLResponse:
        query = (q or "").strip()
        with connect(settings.db_path) as conn:
            results = search_notes(conn, query) if query else []
            tags = list_tags(conn)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "notes": results, "tags": tags, "search_query": query, "active_tag": None},
        )

    @app.get("/notes/new", response_class=HTMLResponse)
    def new_note_form(request: Request) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            tags = list_tags(conn)
        return templates.TemplateResponse(
            "note_form.html",
            {
                "request": request,
                "mode": "create",
                "note": {"title": "", "content": "", "tags": []},
                "tags": tags,
            },
        )

    @app.post("/notes")
    def create_note_action(
        request: Request,
        title: str = Form(""),
        content: str = Form(""),
        tags: str = Form(""),
    ) -> Response:
        tag_list = parse_tags(tags)
        with connect(settings.db_path) as conn:
            nid = create_note(conn, title=title, content=content, tags=tag_list)
        return RedirectResponse(url=f"/notes/{nid}", status_code=303)

    @app.get("/notes/{note_id}", response_class=HTMLResponse)
    def view_note(request: Request, note_id: int) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            note = get_note(conn, note_id)
            tags = list_tags(conn)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        rendered = md.render(note["content"])
        note_view = dict(note)
        note_view["content_html"] = Markup(rendered)  # safe because Markdown renderer disables raw HTML

        return templates.TemplateResponse(
            "note_view.html",
            {"request": request, "note": note_view, "tags": tags},
        )

    @app.get("/notes/{note_id}/edit", response_class=HTMLResponse)
    def edit_note_form(request: Request, note_id: int) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            note = get_note(conn, note_id)
            tags = list_tags(conn)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return templates.TemplateResponse(
            "note_form.html",
            {"request": request, "mode": "edit", "note": note, "tags": tags},
        )

    @app.post("/notes/{note_id}")
    def update_note_action(
        request: Request,
        note_id: int,
        title: str = Form(""),
        content: str = Form(""),
        tags: str = Form(""),
    ) -> Response:
        tag_list = parse_tags(tags)
        with connect(settings.db_path) as conn:
            if not get_note(conn, note_id):
                raise HTTPException(status_code=404, detail="Note not found")
            update_note(conn, note_id, title=title, content=content, tags=tag_list)
        return RedirectResponse(url=f"/notes/{note_id}", status_code=303)

    @app.post("/notes/{note_id}/delete")
    def delete_note_action(request: Request, note_id: int) -> Response:
        with connect(settings.db_path) as conn:
            delete_note(conn, note_id)
        if _is_htmx(request):
            return HTMLResponse("", status_code=200)
        return RedirectResponse(url="/", status_code=303)

    @app.post("/notes/{note_id}/pin", response_class=HTMLResponse)
    def pin_note_action(request: Request, note_id: int) -> HTMLResponse:
        with connect(settings.db_path) as conn:
            toggle_pin(conn, note_id)
            note = get_note(conn, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        # return updated card for HTMX swap
        return templates.TemplateResponse(
            "_note_card.html",
            {"request": request, "n": note, "compact": True},
        )

    @app.get("/export.json")
    def export_json() -> JSONResponse:
        with connect(settings.db_path) as conn:
            data = export_all(conn)
        return JSONResponse({"notes": data})

    # ---- JSON API ----

    @app.get("/api/notes", response_model=list[NoteListItem])
    def api_list(tag: str | None = None) -> list[dict]:
        with connect(settings.db_path) as conn:
            return list_notes(conn, tag=tag)

    @app.get("/api/notes/{note_id}", response_model=NoteOut)
    def api_get(note_id: int) -> dict:
        with connect(settings.db_path) as conn:
            note = get_note(conn, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "db": str(settings.db_path)}

    return app


app = create_app()
