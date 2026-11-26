"""Digests: markdown files with YAML frontmatter that ai-newstand uploads to
``s3://smr-webdev-content/digests/``. The deploy workflow copies them into a local
folder before the build, so this module only ever reads files from disk.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
import markdown

logger = logging.getLogger(__name__)

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


def load_all(directory: Path) -> list[Digest]:
    """Every digest directly in ``directory``, newest first. Subfolders like drafts/
    are skipped. A file that won't parse is logged and left out, so one bad digest
    can't block every deploy after it."""
    found = []
    for file in directory.glob("*.md"):
        if not SLUG_RE.match(file.stem):
            continue
        try:
            found.append(parse(file.stem, file.read_text(encoding="utf-8")))
        except Exception:
            logger.exception("Skipping digest %s", file.name)
    return sorted(found, key=lambda d: d.date, reverse=True)
