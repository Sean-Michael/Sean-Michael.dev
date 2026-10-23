import re

import pytest

from app import main


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
    ],
)
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_pages_get_the_layout(client):
    html = client.get("/about").text
    assert '<header class="site">' in html
    assert "<title>About — Sean-Michael</title>" in html
    assert "---" not in html.split("<main>")[0]


def test_doctype_pages_served_as_is(client):
    res = client.get("/arete/privacy")
    assert res.text == (main.SITE_DIR / "arete" / "privacy.html").read_text()


def test_posts_get_title_and_date(client):
    html = client.get("/blog/mt-hood-summit").text
    assert "<h1>Trip Report: Mt.Hood Summit</h1>" in html
    assert "May 28, 2025" in html


def test_latest_posts_newest_first(client):
    html = client.get("/blog/latest").text
    assert html.index("building-an-ai-news-digest") < html.index("mt-hood-summit")
    assert "<html" not in html
    assert client.get("/blog/latest?limit=1").text.count("<li>") == 1


@pytest.mark.parametrize(
    "path",
    ["/nope", "/blog/nope", "/404", "/blog/..%2F..%2Fapp%2Fmain.py", "/digest/nope"],
)
def test_unknown_paths_404(client, path):
    res = client.get(path)
    assert res.status_code == 404
    assert "Not found" in res.text


def test_every_internal_link_resolves(client):
    paths = set()
    for page in main.SITE_DIR.rglob("*.html"):
        paths |= set(re.findall(r'(?:href|src)="(/[^"#?]*)', page.read_text()))
    broken = [p for p in sorted(paths) if client.get(p).status_code != 200]
    assert not broken


def test_digest_renders_markdown_without_duplicate_title(client):
    html = client.get("/digest/2026-03-30").text
    assert "<h1>Tech Digest: March 30, 2026</h1>" in html
    assert "<h2" in html and "Top Stories" in html


def test_digest_drafts_not_listed(client, store):
    (store.root / "digests" / "drafts").mkdir()
    (store.root / "digests" / "drafts" / "wip.md").write_text("---\ntitle: WIP digest\n---\nx")
    main.digests.refresh()
    assert "WIP digest" not in client.get("/digest").text


def test_refresh_only_fetches_changed_digests(store, monkeypatch):
    digests = main.digests
    (store.root / "digests" / "2026-04-01.md").write_text("---\ntitle: New one\n---\nhello")

    fetched = []
    get = store.get
    monkeypatch.setattr(store, "get", lambda key: fetched.append(key) or get(key))
    digests.refresh()
    assert fetched == ["digests/2026-04-01.md"]
    assert [d.slug for d in digests.list()] == ["2026-04-01", "2026-03-30"]

    (store.root / "digests" / "2026-03-30.md").unlink()
    digests.refresh()
    assert [d.slug for d in digests.list()] == ["2026-04-01"]


def test_sitemap(client):
    xml = client.get("/sitemap.xml").text
    assert "<loc>https://sean-michael.dev/</loc>" in xml
    assert "/blog/mt-hood-summit</loc>" in xml
    assert "/digest/2026-03-30</loc>" in xml
    assert "404" not in xml and "arete" not in xml and "static" not in xml
