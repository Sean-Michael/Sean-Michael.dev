import re
from datetime import date
from io import StringIO
from pathlib import Path

import frontmatter
import markdown
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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


class Digest(BaseModel):
    title: str
    date: date
    content: str
    slug: str


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    blogs = load_all_blogs()
    all_projects = load_all_projects()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "blogs": blogs[:3], "projects": all_projects},
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


def load_all_digests() -> list[Digest]:
    digests = []
    for slug in list_digest_files():
        digests.append(load_digest(slug))
    return sorted(digests, key=lambda d: d.date, reverse=True)


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
    digests = load_all_digests()
    return templates.TemplateResponse("digest_index.html", {"request": request, "digests": digests})


@app.get("/digest/{slug}", response_class=HTMLResponse)
async def get_digest(request: Request, slug: str):
    digest = load_digest(slug)
    return templates.TemplateResponse("digest_detail.html", {"request": request, "digest": digest})


@app.get("/blog", response_class=HTMLResponse)
async def get_blogs(request: Request, tag: str | None = None):
    blogs = load_all_blogs()
    all_tags = get_all_tags(blogs)
    if tag:
        blogs = [b for b in blogs if tag in b.tags]
    return templates.TemplateResponse(
        "blog_index.html",
        {"request": request, "blogs": blogs, "all_tags": all_tags, "active_tag": tag},
    )


@app.get("/blog/{slug}", response_class=HTMLResponse)
def get_blog(request: Request, slug: str):
    blog = load_blog(slug)
    all_blogs = load_all_blogs()
    related = get_related_posts(blog, all_blogs)
    return templates.TemplateResponse(
        "blog_detail.html", {"request": request, "blog": blog, "related_posts": related}
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    all_projects = load_all_projects()
    return templates.TemplateResponse(
        "projects_index.html",
        {"request": request, "projects": all_projects},
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def get_project(request: Request, slug: str):
    project = load_project(slug)
    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": project},
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/partials/sidebar-blogs", response_class=HTMLResponse)
async def sidebar_blogs(request: Request):
    blogs = load_all_blogs()
    return templates.TemplateResponse(
        "partials/sidebar_blogs.html", {"request": request, "blogs": blogs}
    )
