import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURES_CONTENT = Path(__file__).parent / "fixtures" / "data"
os.environ.setdefault("CONTENT_SOURCE", "local")

import app.content as _content  # noqa: E402
from app.content import ContentType  # noqa: E402

_content.CONTENT_CONFIG[ContentType.BLOG]["local_dir"] = FIXTURES_CONTENT / "blog" / "posts"
_content.CONTENT_CONFIG[ContentType.PROJECT]["local_dir"] = (
    FIXTURES_CONTENT / "projects" / "published"
)
_content.CONTENT_CONFIG[ContentType.DIGEST]["local_dir"] = FIXTURES_CONTENT / "digests"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)
