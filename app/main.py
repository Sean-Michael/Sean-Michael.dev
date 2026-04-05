import re
from datetime import date
from io import StringIO
from pathlib import Path

import frontmatter
import markdown
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.content import (
    list_blog_files,
    list_digest_files,
    list_project_files,
    read_blog_file,
    read_digest_file,
    read_project_file,
)

BASE_DIR = Path(__file__).parent.parent
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
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    blogs = load_all_blogs()
    all_projects = load_all_projects()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"blogs": blogs[:3], "projects": all_projects},
    )


def load_digest(slug: str) -> Digest:
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
    """Derive title and date from slug like 'topic-words-2026-04-04'."""
    # Last 3 segments are YYYY-MM-DD
    parts = slug.rsplit("-", 3)
    d = date(int(parts[1]), int(parts[2]), int(parts[3]))
    title_part = parts[0].replace("-", " ").title()
    title = f"{title_part} | {d.isoformat()}"
    return DigestSummary(title=title, date=d, slug=slug)


def list_all_digests() -> list[DigestSummary]:
    summaries = [parse_digest_slug(slug) for slug in list_digest_files()]
    return sorted(summaries, key=lambda d: d.date, reverse=True)


def load_blog(slug: str) -> Blog:
    content = read_blog_file(slug)
    post = frontmatter.load(StringIO(content))

    return Blog.model_validate(
        {
            **post.metadata,
            "content": markdown.markdown(post.content),
            "slug": slug,
        }
    )


def load_all_blogs() -> list[Blog]:
    blogs = []
    for slug in list_blog_files():
        blogs.append(load_blog(slug))
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


def load_project(slug: str) -> Project:
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


def load_all_projects() -> list[Project]:
    projects = []
    for slug in list_project_files():
        projects.append(load_project(slug))
    return sorted(projects, key=lambda p: p.date, reverse=True)


# TODO: can't these be made into one func with optional path?


@app.get("/digest", response_class=HTMLResponse)
async def get_digests(request: Request):
    digests = list_all_digests()
    return templates.TemplateResponse(request, "digest_index.html", {"digests": digests})


@app.get("/digest/{slug}", response_class=HTMLResponse)
async def get_digest(request: Request, slug: str):
    digest = load_digest(slug)
    return templates.TemplateResponse(request, "digest_detail.html", {"digest": digest})


@app.get("/blog", response_class=HTMLResponse)
async def get_blogs(request: Request, tag: str | None = None):
    blogs = load_all_blogs()
    all_tags = get_all_tags(blogs)
    if tag:
        blogs = [b for b in blogs if tag in b.tags]
    return templates.TemplateResponse(
        request,
        "blog_index.html",
        {"blogs": blogs, "all_tags": all_tags, "active_tag": tag},
    )


@app.get("/blog/{slug}", response_class=HTMLResponse)
def get_blog(request: Request, slug: str):
    blog = load_blog(slug)
    all_blogs = load_all_blogs()
    related = get_related_posts(blog, all_blogs)
    return templates.TemplateResponse(
        request, "blog_detail.html", {"blog": blog, "related_posts": related}
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    all_projects = load_all_projects()
    return templates.TemplateResponse(
        request,
        "projects_index.html",
        {"projects": all_projects},
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def get_project(request: Request, slug: str):
    project = load_project(slug)
    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {"project": project},
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html")


@app.get("/partials/sidebar-blogs", response_class=HTMLResponse)
async def sidebar_blogs(request: Request):
    blogs = load_all_blogs()
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
