"""Digests: markdown files with YAML frontmatter that the digest automation writes
to the store under ``digests/``.

Every digest is held in memory, already rendered to HTML. ``refresh()`` runs at
startup and then in the background, and only fetches files whose version
changed, so a page view never waits on S3.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Any

import frontmatter
import markdown

from app.store import Store

logger = logging.getLogger(__name__)

PREFIX = "digests/"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,120}$")
SLUG_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})$")


@dataclass(frozen=True)
class Digest:
    slug: str
    title: str
    date: date
    html: str
    summary: str
    read_time: int

    @property
    def url(self) -> str:
        return f"/digest/{self.slug}"


def _parse_date(value: Any, slug: str) -> date:
    if isinstance(value, date):
        return value
    for text in (str(value or ""), *SLUG_DATE_RE.findall(slug)):
        try:
            return date.fromisoformat(text.strip())
        except ValueError:
            pass
    return date.min


def _summary(body: str) -> str:
    for line in body.strip().splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "-", "```", "<", "!", "|", ">")):
            return line
    return ""


def parse(slug: str, text: str) -> Digest:
    post = frontmatter.loads(text)
    meta = post.metadata
    # Generated digests repeat the title as a leading H1; the page shows it already.
    body = re.sub(r"^#\s+.+\n*", "", post.content, count=1)
    return Digest(
        slug=slug,
        title=str(meta.get("title") or slug.replace("-", " ").title()),
        date=_parse_date(meta.get("date"), slug),
        html=markdown.markdown(body, extensions=["fenced_code", "tables", "toc", "sane_lists"]),
        summary=str(meta.get("description") or _summary(body)),
        read_time=max(1, round(len(body.split()) / 200)),
    )


class Digests:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._by_slug: dict[str, Digest] = {}
        self._versions: dict[str, str] = {}
        self._newest_first: list[Digest] = []
        self._pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="digest-fetch")

    def list(self) -> list[Digest]:
        return self._newest_first

    def get(self, slug: str) -> Digest | None:
        return self._by_slug.get(slug)

    def _load(self, slug: str) -> Digest | None:
        try:
            raw = self.store.get(f"{PREFIX}{slug}.md")
            return None if raw is None else parse(slug, raw.decode("utf-8"))
        except Exception:
            logger.exception("Failed to load digest %s", slug)
            return None

    def refresh(self) -> None:
        listing = {
            name[:-3]: version
            for name, version in self.store.list(PREFIX).items()
            if name.endswith(".md") and SLUG_RE.match(name[:-3])
        }
        # Start from what's still listed; anything that failed to load keeps its old copy
        # and old version, so it's retried next time.
        by_slug = {s: d for s, d in self._by_slug.items() if s in listing}
        versions = {s: v for s, v in self._versions.items() if s in listing}
        changed = [s for s, v in listing.items() if versions.get(s) != v]
        for slug, digest in zip(changed, self._pool.map(self._load, changed)):
            if digest is not None:
                by_slug[slug] = digest
                versions[slug] = listing[slug]

        self._by_slug = by_slug
        self._versions = versions
        self._newest_first = sorted(by_slug.values(), key=lambda d: d.date, reverse=True)
        if changed:
            logger.info("Digests: %d loaded, %d fetched", len(by_slug), len(changed))
