"""Pages in site/: a small YAML header, then any HTML you like.

    ---
    title: "Trip Report: Mt. Hood Summit"
    date: 2025-05-28
    description: One line for search results and link previews.
    tags: [climbing, mountaineering]
    ---
    <p>Write whatever HTML you want here, <style> and <script> tags included.</p>

The URL comes from the file path: site/about.html is /about, site/blog/index.html is
/blog. A page under site/blog/ with a date is a blog post: it gets the post header
(title, date, read time) and shows up in the post lists.

A file that starts with <!doctype html> skips the layout and is sent exactly as written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter

SITE_DIR = (Path(__file__).parent.parent / "site").resolve()
BLOG_DIR = SITE_DIR / "blog"


@dataclass
class Page:
    url: str
    html: str
    title: str = ""
    date: date | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    standalone: bool = False

    @property
    def read_time(self) -> int:
        words = re.sub(r"<[^>]+>", " ", self.html).split()
        return max(1, round(len(words) / 200))


def url_for(file: Path) -> str:
    """site/blog/index.html -> /blog, site/about.html -> /about."""
    rel = file.relative_to(SITE_DIR).with_suffix("")
    parts = rel.parts[:-1] if rel.name == "index" else rel.parts
    return "/" + "/".join(parts)


def find(path: str) -> Path | None:
    """The reverse of url_for: /about -> site/about.html, /blog -> site/blog/index.html."""
    path = path.strip("/")
    for candidate in (SITE_DIR / f"{path}.html", SITE_DIR / path / "index.html"):
        file = candidate.resolve()
        # resolve() collapses any "..", so this blocks URLs that try to escape site/.
        if file.is_relative_to(SITE_DIR) and file.is_file() and file.name != "404.html":
            return file
    return None


def load(file: Path) -> Page:
    post = frontmatter.load(file)
    meta = post.metadata
    day = meta.get("date")
    return Page(
        url=url_for(file),
        html=post.content,
        title=str(meta.get("title", "")),
        date=date.fromisoformat(str(day)) if day else None,
        description=str(meta.get("description", "")),
        tags=list(meta.get("tags", [])),
        standalone=post.content.lstrip().lower().startswith("<!doctype"),
    )


def posts() -> list[Page]:
    """Every blog post, newest first. Read from disk each time, so new files show up."""
    found = [load(f) for f in BLOG_DIR.glob("*.html") if f.name != "index.html"]
    return sorted((p for p in found if p.date), key=lambda p: p.date, reverse=True)
