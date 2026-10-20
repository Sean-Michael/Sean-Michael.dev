.PHONY: dev test lint freeze

# Run the site locally on http://127.0.0.1:8000, with digests from ./content/digests.
dev:
	CONTENT_SOURCE=local uv run uvicorn app.main:app --reload

test:
	uv run pytest -q

lint:
	uv run ruff check app/ tests/
	uv run ruff format app/ tests/

freeze:
	uv pip compile pyproject.toml -o requirements.txt
