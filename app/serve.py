"""Serve dist/ locally the way GitHub Pages does: /about -> about.html, and 404.html
for anything missing. For previewing a build, not for production.

    uv run python -m app.serve        # http://127.0.0.1:8000
"""

from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIST = Path(__file__).parent.parent / "dist"


class PagesHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        fs_path = Path(super().translate_path(path))
        if not fs_path.exists() and fs_path.with_suffix(".html").is_file():
            return str(fs_path.with_suffix(".html"))
        return str(fs_path)

    def send_error(self, code, message=None, explain=None):
        page = DIST / "404.html"
        if code != 404 or not page.is_file():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def main() -> None:
    handler = functools.partial(PagesHandler, directory=str(DIST))
    with ThreadingHTTPServer(("127.0.0.1", 8000), handler) as server:
        print("Serving dist/ on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    main()
