import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import admin
from app.content import content
from app.main import app
from app.store import LocalStore

FIXTURES = Path(__file__).parent / "fixtures" / "data"
ADMIN = {"X-Auth-Request-User": "sean-michael", "Sec-Fetch-Site": "same-origin"}


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    """Every test gets its own copy of the fixture content."""
    shutil.copytree(FIXTURES, tmp_path / "content")
    s = LocalStore(tmp_path / "content")
    monkeypatch.setattr(content, "store", s)
    monkeypatch.setattr(admin, "ADMIN_DEV", False)
    content.clear_cache()
    yield s
    content.clear_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
