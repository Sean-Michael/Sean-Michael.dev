import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/about",
        "/blog",
        "/blog/kubernetes-homelab",
        "/projects",
        "/projects/homelab-cluster",
        "/digest",
        "/digest/2026-03-30",
        "/arete/support",
        "/arete/privacy",
    ],
)
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_home_lists_posts_newest_first(client):
    html = client.get("/").text
    # building-an-ai-news-digest (2026-04-06) is newer than kubernetes-homelab (2026-02-20)
    assert html.index("/blog/building-an-ai-news-digest") < html.index("/blog/kubernetes-homelab")


def test_post_renders_markdown(client):
    html = client.get("/blog/kubernetes-homelab").text
    assert "<h1>Running Kubernetes in My Homelab</h1>" in html
    assert "<h2" in html and "The Setup" in html


def test_tag_filter(client):
    html = client.get("/blog?tag=kubernetes").text
    assert "kubernetes-homelab" in html
    assert "building-an-ai-news-digest" not in html


def test_unknown_and_bad_slugs_404(client):
    assert client.get("/blog/nope").status_code == 404
    assert client.get("/blog/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/projects/Bad_Slug").status_code == 404


def test_drafts_are_not_public(client, store):
    store.put(
        "blog/drafts/secret.md", b"---\ntitle: Secret\ndate: 2026-01-01\n---\nshh", "text/markdown"
    )
    assert client.get("/blog/secret").status_code == 404
    assert "Secret" not in client.get("/blog").text


def test_digest_drafts_not_listed_as_digests(client, store):
    store.put("digests/drafts/wip.md", b"---\ntitle: WIP digest\n---\nx", "text/markdown")
    assert "WIP digest" not in client.get("/digest").text


def test_feed_and_sitemap(client):
    feed = client.get("/blog/feed.xml")
    assert feed.headers["content-type"].startswith("application/rss+xml")
    assert "/blog/kubernetes-homelab" in feed.text
    assert "/projects/homelab-cluster" in client.get("/sitemap.xml").text


def test_images_served_from_store(client, store):
    store.put("images/blog/x/pic.png", b"\x89PNG", "image/png")
    res = client.get("/images/blog/x/pic.png")
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"
    assert client.get("/images/blog/x/notes.md").status_code == 404
