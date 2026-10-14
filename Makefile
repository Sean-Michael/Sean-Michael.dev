.PHONY: dev test lint freeze

# Run the site locally against ./content with the admin page unlocked:
#   http://127.0.0.1:8000        the site
#   http://127.0.0.1:8000/admin  write, preview, publish
dev:
	ADMIN_DEV=1 CONTENT_SOURCE=local uv run uvicorn app.main:app --reload

test:
	uv run pytest -q

lint:
	uv run ruff check app/ tests/
	uv run ruff format app/ tests/

freeze:
	uv pip compile pyproject.toml -o requirements.txt
