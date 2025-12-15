from datetime import date
from pathlib import Path

import frontmatter
import markdown
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content" / "blog"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


class Blog(BaseModel):
    title: str
    date: date
    author: str
    content: str
    slug: str
    tags: list[str] = []


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def load_blog(slug: str) -> Blog:
    with open(CONTENT_DIR / f"{slug}.md") as f:
        post = frontmatter.load(f)

    return Blog.model_validate(
        {
            **post.metadata,
            "content": markdown.markdown(post.content),
            "slug": slug,
        }
    )


def load_all_blogs() -> list[Blog]:
    blogs = []
    for md_file in CONTENT_DIR.glob("*.md"):
        slug = md_file.stem
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


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/partials/sidebar-blogs", response_class=HTMLResponse)
async def sidebar_blogs(request: Request):
    blogs = load_all_blogs()
    return templates.TemplateResponse(
        "partials/sidebar_blogs.html", {"request": request, "blogs": blogs}
    )
