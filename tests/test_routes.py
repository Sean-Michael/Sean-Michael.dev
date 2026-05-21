"""HTTP route tests — every endpoint, status codes, and key response content."""

from fastapi.testclient import TestClient

from app.main import _ttl_bucket, list_all_digests, load_all_blogs, load_all_projects

# ---------------------------------------------------------------------------
# Static / meta routes
# ---------------------------------------------------------------------------


def test_home_returns_200(client: TestClient):
    assert client.get("/").status_code == 200


def test_home_contains_name(client: TestClient):
    assert "Sean-Michael" in client.get("/").text


def test_home_contains_hero_label(client: TestClient):
    assert "SEAN-MICHAEL" in client.get("/").text


def test_home_carousel_widgets_present(client: TestClient):
    html = client.get("/").text
    assert "carousel-widget" in html
    assert "hcr-tab" in html


def test_robots_txt(client: TestClient):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "User-agent" in r.text
    assert "Sitemap" in r.text


def test_sitemap_xml(client: TestClient):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<urlset" in r.text
    assert "sean-michael.dev" in r.text


def test_static_css_served(client: TestClient):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert "oklch" in r.text


def test_js_bundle_served(client: TestClient):
    r = client.get("/js/main.js")
    assert r.status_code == 200


def test_404_page(client: TestClient):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert "404" in r.text


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------


def test_about_returns_200(client: TestClient):
    assert client.get("/about").status_code == 200


def test_about_contains_bellingham(client: TestClient):
    assert "Bellingham" in client.get("/about").text


def test_about_has_hobby_sections(client: TestClient):
    html = client.get("/about").text
    assert "climbing" in html
    assert "guitar" in html


# ---------------------------------------------------------------------------
# Blog index
# ---------------------------------------------------------------------------


def test_blog_index_returns_200(client: TestClient):
    assert client.get("/blog").status_code == 200


def test_blog_index_lists_posts(client: TestClient):
    blogs = load_all_blogs(_ttl_bucket())
    html = client.get("/blog").text
    for blog in blogs:
        assert blog.title in html


def test_blog_index_shows_tag_filters(client: TestClient):
    html = client.get("/blog").text
    assert "pg-tag-pill" in html


def test_blog_tag_filter_returns_200(client: TestClient):
    assert client.get("/blog?tag=python").status_code == 200


def test_blog_tag_filter_excludes_other_posts(client: TestClient):
    blogs = load_all_blogs(_ttl_bucket())
    python_posts = [b for b in blogs if "python" in b.tags]
    other_posts = [b for b in blogs if "python" not in b.tags]

    html = client.get("/blog?tag=python").text
    for post in python_posts:
        assert post.title in html
    for post in other_posts:
        assert post.title not in html


def test_blog_tag_filter_unknown_tag_returns_empty(client: TestClient):
    r = client.get("/blog?tag=zzz-no-such-tag")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Blog detail
# ---------------------------------------------------------------------------


def test_blog_detail_returns_200(client: TestClient):
    slug = load_all_blogs(_ttl_bucket())[0].slug
    assert client.get(f"/blog/{slug}").status_code == 200


def test_blog_detail_contains_title(client: TestClient):
    blog = load_all_blogs(_ttl_bucket())[0]
    html = client.get(f"/blog/{blog.slug}").text
    assert blog.title in html


def test_blog_detail_contains_tags(client: TestClient):
    blog = load_all_blogs(_ttl_bucket())[0]
    html = client.get(f"/blog/{blog.slug}").text
    for tag in blog.tags:
        assert tag in html


def test_blog_detail_has_breadcrumb(client: TestClient):
    slug = load_all_blogs(_ttl_bucket())[0].slug
    html = client.get(f"/blog/{slug}").text
    assert "← blog" in html


def test_blog_detail_missing_returns_404(client: TestClient):
    r = client.get("/blog/no-such-post-ever")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Projects index
# ---------------------------------------------------------------------------


def test_projects_index_returns_200(client: TestClient):
    assert client.get("/projects").status_code == 200


def test_projects_index_lists_projects(client: TestClient):
    projects = load_all_projects(_ttl_bucket())
    html = client.get("/projects").text
    for project in projects:
        assert project.title in html


def test_projects_index_has_status_filters(client: TestClient):
    html = client.get("/projects").text
    assert "wip" in html
    assert "active" in html


# ---------------------------------------------------------------------------
# Project detail
# ---------------------------------------------------------------------------


def test_project_detail_returns_200(client: TestClient):
    slug = load_all_projects(_ttl_bucket())[0].slug
    assert client.get(f"/projects/{slug}").status_code == 200


def test_project_detail_contains_title(client: TestClient):
    project = load_all_projects(_ttl_bucket())[0]
    html = client.get(f"/projects/{project.slug}").text
    assert project.title in html


def test_project_detail_contains_github_link(client: TestClient):
    project = load_all_projects(_ttl_bucket())[0]
    html = client.get(f"/projects/{project.slug}").text
    assert project.github_url in html


def test_project_detail_has_breadcrumb(client: TestClient):
    slug = load_all_projects(_ttl_bucket())[0].slug
    html = client.get(f"/projects/{slug}").text
    assert "← projects" in html


def test_project_detail_missing_returns_404(client: TestClient):
    r = client.get("/projects/no-such-project")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Digest index
# ---------------------------------------------------------------------------


def test_digest_index_returns_200(client: TestClient):
    assert client.get("/digest").status_code == 200


def test_digest_index_lists_digests(client: TestClient):
    digests = list_all_digests(_ttl_bucket())
    html = client.get("/digest").text
    for digest in digests:
        assert str(digest.date.year) in html


# ---------------------------------------------------------------------------
# Digest detail
# ---------------------------------------------------------------------------


def test_digest_detail_returns_200(client: TestClient):
    slug = list_all_digests(_ttl_bucket())[0].slug
    assert client.get(f"/digest/{slug}").status_code == 200


def test_digest_detail_contains_title(client: TestClient):
    digest = list_all_digests(_ttl_bucket())[0]
    html = client.get(f"/digest/{digest.slug}").text
    assert str(digest.date.year) in html


def test_digest_detail_has_breadcrumb(client: TestClient):
    slug = list_all_digests(_ttl_bucket())[0].slug
    html = client.get(f"/digest/{slug}").text
    assert "← digests" in html


def test_digest_detail_missing_returns_404(client: TestClient):
    r = client.get("/digest/9999-99-99")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Partials
# ---------------------------------------------------------------------------


def test_sidebar_blogs_partial_returns_200(client: TestClient):
    assert client.get("/partials/sidebar-blogs").status_code == 200


def test_sidebar_blogs_partial_lists_posts(client: TestClient):
    blogs = load_all_blogs(_ttl_bucket())
    html = client.get("/partials/sidebar-blogs").text
    assert blogs[0].title in html
