from tests.conftest import ADMIN


def _save(client, kind="blog", action="draft", **fields):
    data = {
        "title": "Hello There",
        "slug": "hello-there",
        "date": "2026-10-01",
        "body": "Hi **there**.",
        "is_new": "true",
        "action": action,
        **fields,
    }
    return client.post(f"/admin/{kind}/save", data=data, headers=ADMIN, follow_redirects=False)


def test_admin_requires_forwarded_user(client):
    assert client.get("/admin").status_code == 403
    assert client.get("/admin", headers={"X-Auth-Request-User": "someone-else"}).status_code == 403
    assert client.get("/admin", headers=ADMIN).status_code == 200


def test_admin_post_requires_same_origin(client):
    res = client.post(
        "/admin/preview", data={"body": "x"}, headers={"X-Auth-Request-User": "sean-michael"}
    )
    assert res.status_code == 403
    res = client.post(
        "/admin/preview",
        data={"body": "x"},
        headers={"X-Auth-Request-User": "sean-michael", "Origin": "https://evil.example"},
    )
    assert res.status_code == 403


def test_preview(client):
    res = client.post("/admin/preview", data={"body": "# Hi\n\n*yo*"}, headers=ADMIN)
    assert "<em>yo</em>" in res.text


def test_draft_then_publish_then_unpublish(client, store):
    res = _save(client)
    assert res.status_code == 303
    assert store.get("blog/drafts/hello-there.md") is not None
    assert client.get("/blog/hello-there").status_code == 404

    res = _save(client, action="publish", is_new="false")
    assert res.status_code == 303
    assert store.get("blog/drafts/hello-there.md") is None
    page = client.get("/blog/hello-there")
    assert page.status_code == 200 and "<strong>there</strong>" in page.text

    client.post("/admin/blog/hello-there/unpublish", headers=ADMIN)
    assert client.get("/blog/hello-there").status_code == 404
    assert store.get("blog/drafts/hello-there.md") is not None


def test_editing_published_post_keeps_live_copy_until_publish(client, store):
    _save(client, action="publish")
    _save(client, is_new="false", body="New words.")
    assert "Hi <strong>there</strong>" in client.get("/blog/hello-there").text
    dash = client.get("/admin", headers=ADMIN).text
    assert "published, unpublished edits" in dash


def test_new_slug_collision_rejected(client):
    assert _save(client, slug="kubernetes-homelab").status_code == 422


def test_bad_slug_rejected(client):
    assert _save(client, slug="../../etc").status_code == 422


def test_project_fields_round_trip(client):
    _save(
        client,
        kind="projects",
        action="publish",
        github_url="https://github.com/x/y",
        tech_stack="Go, K8s",
        screenshots="/images/projects/a.png\n/images/projects/b.png",
    )
    html = client.get("/projects/hello-there").text
    assert (
        "https://github.com/x/y" in html and "/images/projects/b.png" in html and "Go, K8s" in html
    )


def test_unknown_frontmatter_preserved(client, store):
    store.put(
        "blog/drafts/keep.md",
        b"---\ntitle: Keep\ndate: 2026-01-01\nauthor: SM\n---\nbody",
        "text/markdown",
    )
    _save(client, slug="keep", title="Keep", is_new="false")
    assert b"author: SM" in store.get("blog/drafts/keep.md")


def test_upload_image(client, store):
    res = client.post(
        "/admin/upload",
        data={"kind": "blog", "slug": "hello-there"},
        files={"file": ("My Pic.PNG", b"\x89PNG", "image/png")},
        headers=ADMIN,
    )
    assert res.status_code == 200
    assert "/images/blog/hello-there/my-pic.png" in res.text
    assert store.get("images/blog/hello-there/my-pic.png") == b"\x89PNG"


def test_upload_rejects_non_images(client):
    res = client.post(
        "/admin/upload",
        data={"kind": "blog"},
        files={"file": ("x.html", b"<script>", "text/html")},
        headers=ADMIN,
    )
    assert res.status_code == 400
