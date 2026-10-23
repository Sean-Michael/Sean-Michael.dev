"""sean-michael.dev.

Pages are HTML files in site/ (see app/pages.py), wrapped in app/templates/base.html.
The digests come from the store (S3 in prod) and are kept in memory by app.digests.
"""

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import pages
from app.digests import Digests
from app.pages import SITE_DIR
from app.store import make_store

SITE = "https://sean-michael.dev"
DIGEST_REFRESH_SECONDS = 300
# Top-level names under site/ that don't belong in the sitemap.
NOT_IN_SITEMAP = {"404.html", "arete", "static"}

logger = logging.getLogger(__name__)
digests = Digests(make_store())


def _refresh_digests() -> None:
    try:
        digests.refresh()
    except Exception:
        logger.exception("Digest refresh failed; serving the last good copy")


async def _refresh_forever() -> None:
    while True:
        await asyncio.sleep(DIGEST_REFRESH_SECONDS)
        await asyncio.to_thread(_refresh_digests)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Load before taking traffic so the first visitor isn't the one who waits.
    await asyncio.to_thread(_refresh_digests)
    task = asyncio.create_task(_refresh_forever())
    yield
    task.cancel()


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=SITE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    page = pages.load(SITE_DIR / "404.html")
    return templates.TemplateResponse(request, "page.html", {"page": page}, status_code=404)


@app.get("/blog/latest")
async def latest_posts(request: Request, limit: int | None = None):
    """The post list as bare <li>s, for htmx to drop into a page."""
    return templates.TemplateResponse(
        request, "partials/post_list.html", {"posts": pages.posts()[:limit]}
    )


@app.get("/digest")
async def digest_index(request: Request):
    return templates.TemplateResponse(request, "digest_index.html", {"digests": digests.list()})


@app.get("/digest/{slug}")
async def digest(request: Request, slug: str):
    item = digests.get(slug)
    if item is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "digest.html", {"item": item})


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nSitemap: {SITE}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap_xml():
    files = [
        f
        for f in SITE_DIR.rglob("*.html")
        if f.relative_to(SITE_DIR).parts[0] not in NOT_IN_SITEMAP
    ]
    urls = sorted(SITE + pages.url_for(f) for f in files)
    urls += [f"{SITE}/digest"] + [SITE + d.url for d in digests.list()]
    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'
    )
    return Response(content=xml, media_type="application/xml")


# Catch-all, so it has to stay last: FastAPI tries routes top to bottom.
@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def page(request: Request, path: str):
    file = pages.find(path)
    if file is None:
        raise HTTPException(status_code=404)
    page = pages.load(file)
    if page.standalone:
        return HTMLResponse(page.html)
    return templates.TemplateResponse(request, "page.html", {"page": page})
