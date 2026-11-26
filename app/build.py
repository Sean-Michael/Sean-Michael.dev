"""Build sean-michael.dev into a folder of plain files any static host can serve.

    uv run python -m app.build                     # -> dist/, digests from content/digests/
    uv run python -m app.build --out site-out --digests /path/to/digests

Each file in site/ keeps its path (site/about.html -> dist/about.html, served at /about).
Digests become dist/digest/index.html and dist/digest/<slug>.html. GitHub Pages serves
/about from about.html on its own, so the URLs match what the old FastAPI app served.

Images live in S3, not git (upload with ./image.sh). Pages say src="/images/x.jpg" and
the build points that at the bucket; --check-images fails the build if one is missing.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app import digests, pages
from app.pages import SITE_DIR, Page

SITE = "https://sean-michael.dev"
ROOT = SITE_DIR.parent
# Top-level names under site/ that don't belong in the sitemap.
NOT_IN_SITEMAP = {"404.html", "arete", "static"}
# <!-- posts --> or <!-- posts:5 --> in a page becomes that many <li>s, newest first.
POST_LIST = re.compile(r"<!--\s*posts(?::(\d+))?\s*-->")
IMAGE_BASE = "https://smr-webdev-content.s3.us-west-2.amazonaws.com/images/"
# Only /images/ in an attribute or CSS url(), so prose that mentions the path is left alone.
# In a srcset, only the first candidate is rewritten.
IMAGE_REF = re.compile(r"""((?:src|href|poster|srcset)=["']|url\(["']?)/images/""")
IMAGE_URL = re.compile(re.escape(IMAGE_BASE) + r"""[^"')\s]+""")

logger = logging.getLogger(__name__)
env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
)


def render(template: str, **context) -> str:
    return env.get_template(template).render(**context)


def link_images(html: str) -> str:
    return IMAGE_REF.sub(lambda m: m[1] + IMAGE_BASE, html)


def missing_images(urls: set[str]) -> list[str]:
    """The URLs in ``urls`` the bucket doesn't serve, with the HTTP status. A 403 can mean
    the object is missing or that the bucket's public-read policy isn't applied."""
    missing = []
    for url in sorted(urls):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10):
                pass
        except urllib.error.HTTPError as e:
            missing.append(f"{url} (HTTP {e.code})")
    return missing


def render_page(page: Page, posts: list[Page]) -> str:
    if page.standalone:
        return link_images(page.html)

    def post_list(match: re.Match) -> str:
        limit = int(match[1]) if match[1] else None
        return render("partials/post_list.html", posts=posts[:limit])

    page = replace(page, html=link_images(POST_LIST.sub(post_list, page.html)))
    return render("page.html", page=page)


def sitemap(urls: list[str]) -> str:
    entries = "\n".join(f"  <url><loc>{SITE}{u}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(out: Path, digest_dir: Path, check_images: bool = False) -> None:
    out = out.resolve()
    # out gets wiped first, so never let it be the repo or anything above it.
    if out == ROOT or out in ROOT.parents or out in SITE_DIR.parents or out == SITE_DIR:
        raise ValueError(f"refusing to build into {out}")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE_DIR / "static", out / "static", ignore=shutil.ignore_patterns(".DS_Store"))

    posts = pages.posts()
    urls = []
    images: set[str] = set()
    for file in sorted(SITE_DIR.rglob("*.html")):
        rel = file.relative_to(SITE_DIR)
        if rel.parts[0] == "static":
            continue
        html = render_page(pages.load(file), posts)
        images |= set(IMAGE_URL.findall(html))
        write(out / rel, html)
        if rel.parts[0] not in NOT_IN_SITEMAP:
            urls.append(pages.url_for(file))

    items = digests.load_all(digest_dir)
    write(out / "digest" / "index.html", render("digest_index.html", digests=items))
    for d in items:
        write(out / "digest" / f"{d.slug}.html", render("digest.html", item=d))
    urls += ["/digest", *(d.url for d in items)]

    write(out / "sitemap.xml", sitemap(sorted(urls)))
    write(out / "robots.txt", f"User-agent: *\nSitemap: {SITE}/sitemap.xml\n")
    # Tells GitHub Pages which domain this is; harmless anywhere else.
    write(out / "CNAME", "sean-michael.dev\n")

    if check_images:
        missing = missing_images(images)
        if missing:
            raise SystemExit(
                "Images S3 won't serve (upload with ./image.sh):\n  " + "\n  ".join(missing)
            )
    logger.info("Built %d pages and %d digests into %s", len(urls), len(items), out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--digests", type=Path, default=ROOT / "content" / "digests")
    parser.add_argument(
        "--check-images", action="store_true", help="fail if a page uses an image not in S3"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build(args.out, args.digests, check_images=args.check_images)


if __name__ == "__main__":
    main()
