"""sean-michael.dev.

Everything under site/ is served as-is: /about is site/about.html, /blog is
site/blog/index.html, /static/style.css is site/static/style.css. The only
dynamic pages are the digests, which come from the store (S3 in prod) and are
kept in memory by app.digests.
"""

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.digests import Digests
from app.store import make_store

SITE = "https://sean-michael.dev"
BASE_DIR = Path(__file__).parent
SITE_DIR = (BASE_DIR.parent / "site").resolve()
DIGEST_REFRESH_SECONDS = 300
# Pages that exist but don't belong in the sitemap.
NOT_IN_SITEMAP = {"404.html", "arete"}

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
templates = Jinja2Templates([BASE_DIR / "templates", SITE_DIR])
NOT_FOUND_HTML = (SITE_DIR / "404.html").read_text()


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return HTMLResponse(NOT_FOUND_HTML, status_code=404)


@app.get("/digest", response_class=HTMLResponse)
async def digest_index(request: Request):
    return templates.TemplateResponse(request, "digest_index.html", {"digests": digests.list()})


@app.get("/digest/{slug}", response_class=HTMLResponse)
async def digest(request: Request, slug: str):
    item = digests.get(slug)
    if item is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "digest.html", {"item": item})


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nSitemap: {SITE}/sitemap.xml\n"


def _page_url(file: Path) -> str:
    rel = file.relative_to(SITE_DIR).with_suffix("")
    parts = rel.parts[:-1] if rel.name == "index" else rel.parts
    return "/" + "/".join(parts)


@app.get("/sitemap.xml")
async def sitemap_xml():
    pages = [
        f
        for f in SITE_DIR.rglob("*.html")
        if f.relative_to(SITE_DIR).parts[0] not in NOT_IN_SITEMAP | {"static"}
    ]
    urls = sorted(SITE + _page_url(f) for f in pages)
    urls += [f"{SITE}/digest"] + [f"{SITE}{d.url}" for d in digests.list()]
    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'
    )
    return Response(content=xml, media_type="application/xml")


def _page_file(path: str) -> Path | None:
    path = path.strip("/")
    candidates = [SITE_DIR / f"{path}.html", SITE_DIR / path / "index.html"] if path else []
    for candidate in candidates or [SITE_DIR / "index.html"]:
        file = candidate.resolve()
        if file.is_relative_to(SITE_DIR) and file.is_file() and file.name != "404.html":
            return file
    return None


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def page(path: str):
    file = _page_file(path)
    if file is None:
        raise HTTPException(status_code=404)
    return FileResponse(file, media_type="text/html; charset=utf-8")
