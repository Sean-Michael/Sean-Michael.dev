"""Blog posts, projects, and digests: markdown files with YAML frontmatter.

Each kind has a published prefix and a drafts prefix in the store. An item can
exist in both at once: the published copy is live, the draft holds pending
edits. Publishing moves the draft over the published copy; unpublishing moves
the published copy back to drafts.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

import frontmatter
import markdown

from app.store import Store, make_store

CACHE_TTL = 300  # seconds; writes through this module clear it immediately
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


class Kind(str, Enum):
    BLOG = "blog"
    PROJECT = "projects"
    DIGEST = "digest"

    @property
    def published_prefix(self) -> str:
        # Keep the layout the bucket already uses so existing content and the
        # digest automation keep working.
        return {
            Kind.BLOG: "blog/posts/",
            Kind.PROJECT: "projects/published/",
            Kind.DIGEST: "digests/",
        }[self]

    @property
    def drafts_prefix(self) -> str:
        return {
            Kind.BLOG: "blog/drafts/",
            Kind.PROJECT: "projects/drafts/",
            Kind.DIGEST: "digests/drafts/",
        }[self]

    @property
    def label(self) -> str:
        return {Kind.BLOG: "Post", Kind.PROJECT: "Project", Kind.DIGEST: "Digest"}[self]


@dataclass
class Item:
    kind: Kind
    slug: str
    title: str
    date: date
    body: str  # raw markdown
    meta: dict[str, Any] = field(default_factory=dict)
    draft: bool = False

    @property
    def tags(self) -> list[str]:
        return list(self.meta.get("tags") or [])

    @property
    def url(self) -> str:
        return f"/{self.kind.value}/{self.slug}"

    @property
    def html(self) -> str:
        return render_markdown(self.body)

    @property
    def read_time(self) -> int:
        return max(1, round(len(self.body.split()) / 200))

    @property
    def summary(self) -> str:
        if self.meta.get("description"):
            return str(self.meta["description"])
        for line in self.body.strip().splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-", "```", "<", "!", "|", ">")):
                return line
        return ""

    def to_markdown(self) -> str:
        meta = {k: v for k, v in self.meta.items() if v not in (None, "", [])}
        meta["title"] = self.title
        meta["date"] = self.date
        return frontmatter.dumps(frontmatter.Post(self.body, **meta)) + "\n"


def render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc", "sane_lists"])


def _parse_date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    return fallback


def parse(kind: Kind, slug: str, text: str, draft: bool = False) -> Item:
    post = frontmatter.loads(text)
    meta = dict(post.metadata)
    title = str(meta.pop("title", "") or slug.replace("-", " ").title())
    d = _parse_date(meta.pop("date", None), date.today())
    meta.pop("slug", None)  # the filename is the slug
    body = post.content
    if kind is Kind.DIGEST:
        # Generated digests repeat the title as a leading H1; the page shows it already.
        body = re.sub(r"^#\s+.+\n*", "", body, count=1)
    return Item(kind=kind, slug=slug, title=title, date=d, body=body, meta=meta, draft=draft)


class Content:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._cache: dict[tuple, tuple[float, Any]] = {}

    # -- caching ---------------------------------------------------------

    def _cached(self, key: tuple, fn):
        hit = self._cache.get(key)
        now = time.monotonic()
        if hit and hit[0] > now:
            return hit[1]
        value = fn()
        self._cache[key] = (now + CACHE_TTL, value)
        return value

    def clear_cache(self) -> None:
        self._cache.clear()

    # -- reads -----------------------------------------------------------

    def _key(self, kind: Kind, slug: str, draft: bool) -> str:
        if not SLUG_RE.match(slug):
            raise ValueError(f"invalid slug: {slug!r}")
        prefix = kind.drafts_prefix if draft else kind.published_prefix
        return f"{prefix}{slug}.md"

    def _load(self, kind: Kind, slug: str, draft: bool) -> Item | None:
        try:
            key = self._key(kind, slug, draft)
        except ValueError:
            return None
        raw = self.store.get(key)
        return None if raw is None else parse(kind, slug, raw.decode("utf-8"), draft)

    def _slugs(self, kind: Kind, draft: bool) -> list[str]:
        prefix = kind.drafts_prefix if draft else kind.published_prefix
        names = self.store.list(prefix)
        return [n[:-3] for n in names if n.endswith(".md") and SLUG_RE.match(n[:-3])]

    def get(self, kind: Kind, slug: str, draft: bool = False) -> Item | None:
        return self._cached(("get", kind, slug, draft), lambda: self._load(kind, slug, draft))

    def list(self, kind: Kind, draft: bool = False) -> list[Item]:
        def load() -> list[Item]:
            items = [self._load(kind, s, draft) for s in self._slugs(kind, draft)]
            return sorted((i for i in items if i), key=lambda i: i.date, reverse=True)

        return self._cached(("list", kind, draft), load)

    # -- writes (admin) --------------------------------------------------

    def save_draft(self, item: Item) -> None:
        key = self._key(item.kind, item.slug, draft=True)
        self.store.put(key, item.to_markdown().encode(), "text/markdown; charset=utf-8")
        self.clear_cache()

    def publish(self, kind: Kind, slug: str) -> None:
        draft_key = self._key(kind, slug, draft=True)
        raw = self.store.get(draft_key)
        if raw is None:
            raise LookupError(f"no draft for {kind.value}/{slug}")
        self.store.put(self._key(kind, slug, draft=False), raw, "text/markdown; charset=utf-8")
        self.store.delete(draft_key)
        self.clear_cache()

    def unpublish(self, kind: Kind, slug: str) -> None:
        pub_key = self._key(kind, slug, draft=False)
        raw = self.store.get(pub_key)
        if raw is None:
            raise LookupError(f"{kind.value}/{slug} is not published")
        draft_key = self._key(kind, slug, draft=True)
        if self.store.get(draft_key) is None:
            self.store.put(draft_key, raw, "text/markdown; charset=utf-8")
        self.store.delete(pub_key)
        self.clear_cache()

    def delete_draft(self, kind: Kind, slug: str) -> None:
        self.store.delete(self._key(kind, slug, draft=True))
        self.clear_cache()


content = Content(make_store())
