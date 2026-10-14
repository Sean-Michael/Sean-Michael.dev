"""/admin: write, preview, draft, and publish content.

Authentication is NOT done here. In production Traefik sends every /admin
request through oauth2-proxy (GitHub login) first, and forwards the signed-in
username as ``X-Auth-Request-User``. This module only checks that username
against ADMIN_GITHUB_USERS, as a second lock on the door.

For local development set ADMIN_DEV=1 to skip the check.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from app.content import SLUG_RE, Item, Kind, content, render_markdown

ADMIN_USERS = {
    u.strip().lower()
    for u in os.getenv("ADMIN_GITHUB_USERS", "sean-michael").split(",")
    if u.strip()
}
ADMIN_DEV = os.getenv("ADMIN_DEV") == "1"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def require_admin(request: Request) -> str:
    if ADMIN_DEV:
        user = "dev"
    else:
        user = request.headers.get("x-auth-request-user", "")
        if user.lower() not in ADMIN_USERS:
            raise HTTPException(status_code=403, detail="Not allowed")
    if request.method != "GET" and not _same_origin(request):
        raise HTTPException(status_code=403, detail="Cross-site request blocked")
    return user


def _same_origin(request: Request) -> bool:
    if request.headers.get("sec-fetch-site") == "same-origin":
        return True
    origin = request.headers.get("origin")
    return bool(origin) and urlparse(origin).netloc == request.headers.get("host")


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def _split(value: str, sep: str = ",") -> list[str]:
    return [v.strip() for v in value.split(sep) if v.strip()]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    content.clear_cache()  # always show the real state of the store here
    sections = []
    for kind in Kind:
        drafts = {i.slug: i for i in content.list(kind, draft=True)}
        published = {i.slug: i for i in content.list(kind)}
        rows = []
        for slug in sorted(drafts.keys() | published.keys()):
            item = drafts.get(slug) or published[slug]
            if slug in published and slug in drafts:
                status = "published, unpublished edits"
            elif slug in published:
                status = "published"
            else:
                status = "draft"
            rows.append({"item": item, "status": status})
        rows.sort(key=lambda r: r["item"].date, reverse=True)
        sections.append({"kind": kind, "rows": rows})
    return templates.TemplateResponse(request, "admin/dashboard.html", {"sections": sections})


@router.get("/{kind}/new", response_class=HTMLResponse)
async def new_item(request: Request, kind: Kind):
    item = Item(kind=kind, slug="", title="", date=date.today(), body="")
    return _editor(request, item, is_new=True)


@router.get("/{kind}/{slug}/edit", response_class=HTMLResponse)
async def edit_item(request: Request, kind: Kind, slug: str, saved: str | None = None):
    content.clear_cache()
    item = content.get(kind, slug, draft=True) or content.get(kind, slug)
    if item is None:
        raise HTTPException(status_code=404)
    return _editor(request, item, is_new=False, saved=saved)


def _editor(request: Request, item: Item, is_new: bool, saved=None, error=None, status_code=200):
    published = None if is_new else content.get(item.kind, item.slug)
    has_draft = not is_new and content.get(item.kind, item.slug, draft=True) is not None
    return templates.TemplateResponse(
        request,
        "admin/editor.html",
        {
            "item": item,
            "kind": item.kind,
            "is_new": is_new,
            "is_published": published is not None,
            "has_draft": has_draft,
            "saved": saved,
            "error": error,
        },
        status_code=status_code,
    )


@router.post("/{kind}/save")
async def save_item(
    request: Request,
    kind: Kind,
    title: str = Form(...),
    slug: str = Form(""),
    date_: str = Form("", alias="date"),
    tags: str = Form(""),
    description: str = Form(""),
    body: str = Form(""),
    github_url: str = Form(""),
    demo_url: str = Form(""),
    tech_stack: str = Form(""),
    screenshots: str = Form(""),
    is_new: bool = Form(False),
    action: str = Form("draft"),
):
    slug = slug.strip() or slugify(title)
    try:
        d = date.fromisoformat(date_) if date_ else date.today()
    except ValueError:
        d = date.today()

    existing = content.get(kind, slug, draft=True) or content.get(kind, slug)
    meta = dict(existing.meta) if existing else {}  # keep frontmatter keys the form doesn't know
    meta.update({"tags": _split(tags), "description": description.strip()})
    if kind is Kind.PROJECT:
        meta.update(
            {
                "github_url": github_url.strip(),
                "demo_url": demo_url.strip(),
                "tech_stack": _split(tech_stack),
                "screenshots": _split(screenshots, "\n"),
            }
        )
    item = Item(
        kind=kind,
        slug=slug,
        title=title.strip(),
        date=d,
        body=body.replace("\r\n", "\n"),
        meta=meta,
    )

    if not SLUG_RE.match(slug):
        return _editor(
            request,
            item,
            is_new,
            error="Slug must be lowercase letters, numbers and dashes.",
            status_code=422,
        )
    if is_new and existing is not None:
        return _editor(
            request,
            item,
            is_new,
            error=f"“{slug}” already exists. Pick another slug.",
            status_code=422,
        )

    content.save_draft(item)
    if action == "publish":
        content.publish(kind, slug)
    saved = "published" if action == "publish" else "draft"
    return RedirectResponse(f"/admin/{kind.value}/{slug}/edit?saved={saved}", status_code=303)


@router.post("/{kind}/{slug}/unpublish")
async def unpublish_item(kind: Kind, slug: str):
    try:
        content.unpublish(kind, slug)
    except (LookupError, ValueError):
        raise HTTPException(status_code=404)
    return RedirectResponse(f"/admin/{kind.value}/{slug}/edit?saved=unpublished", status_code=303)


@router.post("/{kind}/{slug}/discard")
async def discard_draft(kind: Kind, slug: str):
    try:
        content.delete_draft(kind, slug)
    except ValueError:
        raise HTTPException(status_code=404)
    if content.get(kind, slug) is not None:
        return RedirectResponse(f"/admin/{kind.value}/{slug}/edit", status_code=303)
    return RedirectResponse("/admin", status_code=303)


@router.post("/preview", response_class=HTMLResponse)
async def preview(body: str = Form("")):
    return HTMLResponse(render_markdown(body))


@router.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile, kind: Kind = Form(...), slug: str = Form("")):
    name = Path(file.filename or "").name
    stem, ext = Path(name).stem, Path(name).suffix.lower()
    if ext not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Images only (png, jpg, gif, webp)")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is over 10 MB")
    folder = slug if SLUG_RE.match(slug) else "unsorted"
    path = f"{kind.value}/{folder}/{slugify(stem) or 'image'}{ext}"
    content.store.put(f"images/{path}", data, file.content_type or "application/octet-stream")
    url = f"/images/{path}"
    return HTMLResponse(
        f'<li><img src="{escape(url)}" alt=""><code>![{escape(stem)}]({escape(url)})</code></li>'
    )
