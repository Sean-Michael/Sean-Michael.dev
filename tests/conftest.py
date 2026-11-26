import shutil
from pathlib import Path

import pytest

from app.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture
def content(tmp_path) -> Path:
    """A private copy of the fixture digests, so a test can add files to it."""
    shutil.copytree(FIXTURES, tmp_path / "content")
    return tmp_path / "content"


@pytest.fixture
def dist(tmp_path, content) -> Path:
    out = tmp_path / "dist"
    build(out, content / "digests")
    return out


@pytest.fixture
def get(dist):
    """Look up a URL the way GitHub Pages does. Returns the file's text, or None for a 404."""

    def get(url: str) -> str | None:
        path = url.split("?")[0].strip("/")
        for candidate in (dist / path, dist / f"{path}.html", dist / path / "index.html"):
            file = candidate.resolve()
            if file.is_relative_to(dist) and file.is_file() and file.name != "404.html":
                return file.read_text(errors="replace")  # images too
        return None

    return get
