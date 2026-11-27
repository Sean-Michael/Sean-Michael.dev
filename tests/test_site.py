import re

import pytest

from app import build as build_module
from app.build import IMAGE_BASE, build
from app.pages import SITE_DIR


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/about",
        "/blog",
        "/blog/",
        "/blog/mt-hood-summit",
        "/projects",
        "/projects/librarius",
        "/digest",
        "/digest/2026-03-30",
        "/arete/support",
        "/arete/privacy",
        "/static/style.css",
        "/robots.txt",
        "/sitemap.xml",
    ],
)
def test_pages_build(get, path):
    assert get(path) is not None


def test_pages_get_the_layout(get):
    html = get("/about")
    assert '<header class="site">' in html
    assert "<title>About — Sean-Michael</title>" in html
    assert "---" not in html.split("<main>")[0]


def test_doctype_pages_copied_as_is(get):
    assert get("/arete/privacy") == (SITE_DIR / "arete" / "privacy.html").read_text()


def test_posts_get_title_and_date(get):
    html = get("/blog/mt-hood-summit")
    assert "<h1>Trip Report: Mt.Hood Summit</h1>" in html
    assert "May 28, 2025" in html


def test_post_lists_filled_in_newest_first(get):
    blog = get("/blog")
    assert blog.index("building-an-ai-news-digest") < blog.index("mt-hood-summit")
    assert "<!-- posts" not in blog

    home = get("/")
    home_list = home.split("<h2>Writing</h2>")[1].split("</ul>")[0]
    assert 1 <= home_list.count("<li>") <= 5


@pytest.mark.parametrize("path", ["/nope", "/blog/nope", "/404", "/digest/nope"])
def test_unknown_paths_404(get, path):
    assert get(path) is None


def test_404_page_has_the_layout(dist):
    html = (dist / "404.html").read_text()
    assert "Not found" in html and '<header class="site">' in html


def test_every_internal_link_resolves(dist, get):
    paths = set()
    for page in dist.rglob("*.html"):
        paths |= set(re.findall(r'(?:href|src)="(/[^"#?]*)', page.read_text()))
    broken = [p for p in sorted(paths) if get(p) is None]
    assert not broken


def test_no_htmx_left(dist):
    for page in dist.rglob("*.html"):
        assert "hx-get" not in page.read_text(), page


def test_digest_renders_markdown_without_duplicate_title(get):
    html = get("/digest/2026-03-30")
    assert "<h1>Tech Digest: March 30, 2026</h1>" in html
    assert "<h2" in html and "Top Stories" in html


def test_digest_drafts_not_listed(tmp_path, content):
    (content / "digests" / "drafts").mkdir()
    (content / "digests" / "drafts" / "wip.md").write_text("---\ntitle: WIP digest\n---\nx")
    build(tmp_path / "out", content / "digests")
    assert "WIP digest" not in (tmp_path / "out" / "digest" / "index.html").read_text()


def test_bad_digest_skipped_not_fatal(tmp_path, content):
    (content / "digests" / "2026-04-01.md").write_text("---\ntitle: [unclosed\n---\nx")
    build(tmp_path / "out", content / "digests")
    index = (tmp_path / "out" / "digest" / "index.html").read_text()
    assert "/digest/2026-03-30" in index
    assert not (tmp_path / "out" / "digest" / "2026-04-01.html").exists()


def test_missing_digest_folder_builds_empty(tmp_path):
    build(tmp_path / "out", tmp_path / "nowhere")
    assert "Nothing here yet." in (tmp_path / "out" / "digest" / "index.html").read_text()


def test_refuses_to_wipe_the_repo():
    with pytest.raises(ValueError):
        build(SITE_DIR.parent, SITE_DIR.parent / "content" / "digests")


def test_sitemap(get):
    xml = get("/sitemap.xml")
    assert "<loc>https://sean-michael.dev/</loc>" in xml
    assert "/blog/mt-hood-summit</loc>" in xml
    assert "/digest/2026-03-30</loc>" in xml
    # Folder pages are listed where Pages serves them, not at the /blog -> /blog/ redirect.
    assert "<loc>https://sean-michael.dev/blog/</loc>" in xml
    assert "<loc>https://sean-michael.dev/digest/</loc>" in xml
    assert "<loc>https://sean-michael.dev/blog</loc>" not in xml
    assert "404" not in xml and "arete" not in xml and "static" not in xml


def test_custom_domain_file(dist):
    assert (dist / "CNAME").read_text().strip() == "sean-michael.dev"


def test_images_point_at_s3(get):
    assert f'src="{IMAGE_BASE}smr-amie.jpg"' in get("/about")
    assert 'src="/images/' not in get("/about")


def test_image_rewrite_leaves_prose_alone():
    html = (
        '<img src="/images/a.jpg"><p>files go in /images/ on S3</p>'
        '<div style="background:url(/images/b.png)">'
    )
    out = build_module.link_images(html)
    assert f'src="{IMAGE_BASE}a.jpg"' in out
    assert f"url({IMAGE_BASE}b.png)" in out
    assert "files go in /images/ on S3" in out


def test_check_images_fails_build_on_missing(tmp_path, content, monkeypatch):
    monkeypatch.setattr(build_module, "missing_images", lambda urls: sorted(urls))
    with pytest.raises(SystemExit, match="smr-amie.jpg"):
        build(tmp_path / "out", content / "digests", check_images=True)


def test_no_image_files_in_repo():
    """Images belong in S3 (./image.sh), not git."""
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".avif"}
    found = [p for p in SITE_DIR.rglob("*") if p.suffix.lower() in exts]
    assert not found, f"upload these with ./image.sh instead: {found}"
