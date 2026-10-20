import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.digests import Digests
from app.store import LocalStore

FIXTURES = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    """Every test gets its own copy of the fixture digests, already loaded."""
    shutil.copytree(FIXTURES, tmp_path / "content")
    s = LocalStore(tmp_path / "content")
    digests = Digests(s)
    digests.refresh()
    monkeypatch.setattr(main, "digests", digests)
    return s


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)
