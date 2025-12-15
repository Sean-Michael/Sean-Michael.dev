from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sean-Michael" in response.text


def test_about_page():
    response = client.get("/about")
    assert response.status_code == 200


def test_blog_index():
    response = client.get("/blog")
    assert response.status_code == 200




def test_sidebar_blogs():
    response = client.get("/partials/sidebar-blogs")
    assert response.status_code == 200
