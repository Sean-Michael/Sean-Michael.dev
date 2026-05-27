import re
import time
from datetime import date
from functools import lru_cache
from io import StringIO
from pathlib import Path

import frontmatter
import markdown
import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.content import (
    ContentNotFoundError,
    list_blog_files,
    list_digest_files,
    list_project_files,
    read_blog_file,
    read_digest_file,
    read_project_file,
)
from app.tides.router import router as tides_router

CACHE_TTL = 300  # 5 minutes


def _ttl_bucket(ttl: int = CACHE_TTL) -> int:
    """Return a value that changes every `ttl` seconds, for lru_cache expiry."""
    return int(time.monotonic() // ttl)


BASE_DIR = Path(__file__).parent.parent
WIDGETS_CONFIG = BASE_DIR / "config" / "widgets.yaml"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

"""
TODO:
- [ ] Refactor some of these functions to be more abstract of Blog/Project/Digest
"""


class Blog(BaseModel):
    title: str
    date: date
    author: str
    content: str
    slug: str
    tags: list[str] = []
    read_time: int = 0
    toc: list[dict] = []


class Project(BaseModel):
    title: str
    date: date
    content: str
    slug: str
    author: str = "Sean-Michael"
    github_url: str
    demo_url: str | None = None
    tech_stack: list[str] = []
    status: str = "active"
    tags: list[str] = []
    description: str = ""


class DigestSummary(BaseModel):
    title: str
    date: date
    slug: str


class Digest(DigestSummary):
    content: str


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_JS_DIST = BASE_DIR / "frontend" / "dist"
if _JS_DIST.is_dir():
    app.mount("/js", StaticFiles(directory=str(_JS_DIST)), name="js")


@app.middleware("http")
async def revalidate_bundles(request: Request, call_next):
    # The Vite bundles have stable, unhashed names (/js/main.js, /js/tides.js),
    # so without this browsers heuristically cache them and miss new deploys.
    # `no-cache` keeps the cached copy but forces an ETag revalidation each load
    # (cheap 304 when unchanged, fresh 200 right after a deploy).
    response = await call_next(request)
    if request.url.path.startswith("/js/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.include_router(tides_router)


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", status_code=404)


@app.exception_handler(ContentNotFoundError)
async def content_not_found(request: Request, exc: ContentNotFoundError):
    return templates.TemplateResponse(request, "404.html", status_code=404)


@lru_cache(maxsize=1)
def load_widget_config(_ttl: int = 0) -> dict:
    if WIDGETS_CONFIG.exists():
        return yaml.safe_load(WIDGETS_CONFIG.read_text()) or {}
    return {}


def _reading_context(cfg: dict) -> dict:
    r = cfg.get("reading") or {}
    total = r.get("total_pages", 0)
    current = r.get("current_page", 0)
    pct = round(current / total * 100) if total else 0
    quote = r.get("quote", "")
    highlight = r.get("quote_highlight", "")
    if highlight and highlight in quote:
        quote_html = quote.replace(highlight, f"<em>{highlight}</em>", 1)
    else:
        quote_html = quote
    return {**r, "progress_pct": pct, "quote_html": quote_html}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ttl = _ttl_bucket()
    blogs = load_all_blogs(ttl)
    all_projects = load_all_projects(ttl)
    cfg = load_widget_config(ttl)

    pinned = (cfg.get("featured_project") or {}).get("slug", "")
    if pinned:
        featured = next((p for p in all_projects if p.slug == pinned), None)
    else:
        featured = next((p for p in all_projects if p.status == "wip"), None)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "blogs": blogs[:3],
            "projects": all_projects,
            "featured": featured,
            "reading": _reading_context(cfg),
            "now": cfg.get("now") or {},
        },
    )


@lru_cache(maxsize=128)
def load_digest(slug: str, _ttl: int = 0) -> Digest:
    content = read_digest_file(slug)
    post = frontmatter.load(StringIO(content))

    # Strip leading H1 from markdown body since the template renders the title separately
    body = re.sub(r"^#\s+.+\n*", "", post.content, count=1)

    return Digest.model_validate(
        {
            **post.metadata,
            "content": markdown.markdown(body),
            "slug": slug,
        }
    )


def parse_digest_slug(slug: str) -> DigestSummary:
    """Derive title and date from slug. Handles 'YYYY-MM-DD' or 'topic-words-YYYY-MM-DD'."""
    parts = slug.rsplit("-", 3)
    if len(parts) == 3:
        d = date(int(parts[0]), int(parts[1]), int(parts[2]))
        title = f"Digest · {d.strftime('%B %d, %Y')}"
    else:
        d = date(int(parts[1]), int(parts[2]), int(parts[3]))
        title_part = parts[0].replace("-", " ").title()
        title = f"{title_part} · {d.strftime('%B %d, %Y')}"
    return DigestSummary(title=title, date=d, slug=slug)


@lru_cache(maxsize=1)
def list_all_digests(_ttl: int = 0) -> list[DigestSummary]:
    summaries = [parse_digest_slug(slug) for slug in list_digest_files()]
    return sorted(summaries, key=lambda d: d.date, reverse=True)


def _flatten_toc(tokens: list, max_level: int = 3) -> list[dict]:
    result = []
    for t in tokens:
        if t["level"] <= max_level:
            result.append({"id": t["id"], "title": t["name"], "level": t["level"]})
        result.extend(_flatten_toc(t.get("children", []), max_level))
    return result


@lru_cache(maxsize=128)
def load_blog(slug: str, _ttl: int = 0) -> Blog:
    content = read_blog_file(slug)
    post = frontmatter.load(StringIO(content))

    md = markdown.Markdown(extensions=["toc"])
    html_content = md.convert(post.content)
    toc = _flatten_toc(md.toc_tokens)
    read_time = max(1, round(len(post.content.split()) / 200))

    return Blog.model_validate(
        {
            **post.metadata,
            "content": html_content,
            "slug": slug,
            "read_time": read_time,
            "toc": toc,
        }
    )


@lru_cache(maxsize=1)
def load_all_blogs(_ttl: int = 0) -> list[Blog]:
    blogs = []
    for slug in list_blog_files():
        blogs.append(load_blog(slug, _ttl))
    return sorted(blogs, key=lambda b: b.date, reverse=True)


def get_all_tags(blogs: list[Blog]) -> list[str]:
    tags = set()
    for blog in blogs:
        tags.update(blog.tags)
    return sorted(tags)


def get_related_posts(current: Blog, all_blogs: list[Blog], limit: int = 5) -> list[Blog]:
    others = [b for b in all_blogs if b.slug != current.slug]

    def score(b: Blog) -> tuple:
        matches = len(set(b.tags) & set(current.tags))
        return (-matches, -b.date.toordinal())

    return sorted(others, key=score)[:limit]


def extract_first_paragraph(text: str) -> str:
    for line in text.strip().splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "-", "```")):
            return line
    return ""


@lru_cache(maxsize=64)
def load_project(slug: str, _ttl: int = 0) -> Project:
    content = read_project_file(slug)
    post = frontmatter.load(StringIO(content))

    description = post.metadata.get("description", "") or extract_first_paragraph(post.content)

    return Project.model_validate(
        {
            **post.metadata,
            "content": markdown.markdown(post.content),
            "slug": slug,
            "description": description,
        }
    )


@lru_cache(maxsize=1)
def load_all_projects(_ttl: int = 0) -> list[Project]:
    projects = []
    for slug in list_project_files():
        projects.append(load_project(slug, _ttl))
    return sorted(projects, key=lambda p: p.date, reverse=True)


# TODO: can't these be made into one func with optional path?


@app.get("/digest", response_class=HTMLResponse)
async def get_digests(request: Request):
    digests = list_all_digests(_ttl_bucket())
    return templates.TemplateResponse(request, "digest_index.html", {"digests": digests})


@app.get("/digest/{slug}", response_class=HTMLResponse)
async def get_digest(request: Request, slug: str):
    digest = load_digest(slug, _ttl_bucket())
    return templates.TemplateResponse(request, "digest_detail.html", {"digest": digest})


@app.get("/blog", response_class=HTMLResponse)
async def get_blogs(request: Request, tag: str | None = None):
    blogs = load_all_blogs(_ttl_bucket())
    all_tags = get_all_tags(blogs)
    if tag:
        blogs = [b for b in blogs if tag in b.tags]
    return templates.TemplateResponse(
        request,
        "blog_index.html",
        {"blogs": blogs, "all_tags": all_tags, "active_tag": tag},
    )


@app.get("/blog/feed.xml")
async def blog_rss():
    blogs = load_all_blogs(_ttl_bucket())
    items = []
    for blog in blogs:
        pub = blog.date.strftime("%a, %d %b %Y 00:00:00 +0000")
        tags = "".join(f"<category>{t}</category>" for t in blog.tags)
        items.append(
            f"<item>"
            f"<title>{blog.title}</title>"
            f"<link>{SITE}/blog/{blog.slug}</link>"
            f"<guid>{SITE}/blog/{blog.slug}</guid>"
            f"<pubDate>{pub}</pubDate>"
            f"<author>{blog.author}</author>"
            f"{tags}"
            f"<description><![CDATA[{blog.content}]]></description>"
            f"</item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        "<channel>"
        f"<title>Sean-Michael — Notes from the field</title>"
        f"<link>{SITE}/blog</link>"
        "<description>Notes on platform engineering, AI, and infrastructure.</description>"
        f'<atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(items)
        + "</channel></rss>"
    )
    return Response(content=feed, media_type="application/rss+xml")


@app.get("/blog/{slug}", response_class=HTMLResponse)
def get_blog(request: Request, slug: str):
    ttl = _ttl_bucket()
    blog = load_blog(slug, ttl)
    all_blogs = load_all_blogs(ttl)
    related = get_related_posts(blog, all_blogs)
    return templates.TemplateResponse(
        request, "blog_detail.html", {"blog": blog, "related_posts": related}
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    all_projects = load_all_projects(_ttl_bucket())
    return templates.TemplateResponse(
        request,
        "projects_index.html",
        {"projects": all_projects},
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def get_project(request: Request, slug: str):
    project = load_project(slug, _ttl_bucket())
    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {"project": project},
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html")


@app.get("/tides", response_class=HTMLResponse)
async def tides_dashboard(request: Request):
    # Full-screen React dashboard; data is fetched client-side from /api/tides.
    return templates.TemplateResponse(request, "tides.html")


@app.get("/partials/sidebar-blogs", response_class=HTMLResponse)
async def sidebar_blogs(request: Request):
    blogs = load_all_blogs(_ttl_bucket())
    return templates.TemplateResponse(request, "partials/sidebar_blogs.html", {"blogs": blogs})


SITE = "https://sean-michael.dev"


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap_xml():
    urls = [
        SITE,
        f"{SITE}/blog",
        f"{SITE}/digest",
        f"{SITE}/projects",
        f"{SITE}/about",
        f"{SITE}/tides",
    ]
    for slug in list_blog_files():
        urls.append(f"{SITE}/blog/{slug}")
    for slug in list_digest_files():
        urls.append(f"{SITE}/digest/{slug}")
    for slug in list_project_files():
        urls.append(f"{SITE}/projects/{slug}")

    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'
    return Response(content=xml, media_type="application/xml")
