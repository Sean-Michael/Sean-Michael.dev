import mimetypes
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.admin import router as admin_router
from app.content import Kind, content

SITE = "https://sean-michael.dev"
BASE_DIR = Path(__file__).parent
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.include_router(admin_router)


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", status_code=404)


def _get_or_404(kind: Kind, slug: str):
    item = content.get(kind, slug)
    if item is None:
        raise HTTPException(status_code=404)
    return item


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "posts": content.list(Kind.BLOG),
            "projects": content.list(Kind.PROJECT)[:4],
            "digests": content.list(Kind.DIGEST)[:3],
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html")


@app.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request, tag: str | None = None):
    posts = content.list(Kind.BLOG)
    if tag:
        posts = [p for p in posts if tag in p.tags]
    return templates.TemplateResponse(request, "blog_index.html", {"posts": posts, "tag": tag})


@app.get("/blog/feed.xml")
async def blog_feed():
    items = []
    for p in content.list(Kind.BLOG):
        link = f"{SITE}{p.url}"
        items.append(
            f"<item><title>{escape(p.title)}</title><link>{link}</link>"
            f"<guid>{link}</guid>"
            f"<pubDate>{p.date.strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>"
            f"<description><![CDATA[{p.html}]]></description></item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f"<title>Sean-Michael</title><link>{SITE}/blog</link>"
        "<description>Writing from Sean-Michael.</description>"
        f'<atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(items)
        + "</channel></rss>"
    )
    return Response(content=feed, media_type="application/rss+xml")


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    return templates.TemplateResponse(request, "post.html", {"item": _get_or_404(Kind.BLOG, slug)})


@app.get("/projects", response_class=HTMLResponse)
async def projects_index(request: Request):
    return templates.TemplateResponse(
        request, "projects_index.html", {"projects": content.list(Kind.PROJECT)}
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def project(request: Request, slug: str):
    return templates.TemplateResponse(
        request, "project.html", {"item": _get_or_404(Kind.PROJECT, slug)}
    )


@app.get("/digest", response_class=HTMLResponse)
async def digest_index(request: Request):
    return templates.TemplateResponse(
        request, "digest_index.html", {"digests": content.list(Kind.DIGEST)}
    )


@app.get("/digest/{slug}", response_class=HTMLResponse)
async def digest(request: Request, slug: str):
    return templates.TemplateResponse(
        request, "post.html", {"item": _get_or_404(Kind.DIGEST, slug)}
    )


@app.get("/images/{path:path}")
async def image(path: str):
    """Images uploaded from /admin live in the store under images/."""
    if Path(path).suffix.lower() not in IMAGE_TYPES or ".." in path.split("/"):
        raise HTTPException(status_code=404)
    data = content.store.get(f"images/{path}")
    if data is None:
        raise HTTPException(status_code=404)
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return Response(data, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})


# Standalone pages for the Arete iOS app (App Store "Support URL"). Not linked
# from the nav; reachable only by direct link.
@app.get("/arete/support", response_class=HTMLResponse)
async def arete_support(request: Request):
    return templates.TemplateResponse(request, "arete_support.html")


@app.get("/arete/privacy", response_class=HTMLResponse)
async def arete_privacy(request: Request):
    return templates.TemplateResponse(request, "arete_privacy.html")


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nDisallow: /admin\nSitemap: {SITE}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap_xml():
    urls = [SITE, f"{SITE}/blog", f"{SITE}/projects", f"{SITE}/digest", f"{SITE}/about"]
    for kind in Kind:
        urls += [f"{SITE}{i.url}" for i in content.list(kind)]
    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'
    )
    return Response(content=xml, media_type="application/xml")
