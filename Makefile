.PHONY: build dev test lint freeze

# Build the site into dist/, with digests from ./content/digests.
build:
	uv run python -m app.build

# Build, then preview on http://127.0.0.1:8000. Re-run `make build` after edits.
dev: build
	uv run python -m app.serve

test:
	uv run pytest -q

lint:
	uv run ruff check app/ tests/
	uv run ruff format app/ tests/

freeze:
	uv pip compile pyproject.toml -o requirements.txt
