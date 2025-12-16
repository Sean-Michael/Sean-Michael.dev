.PHONY: dev test lint check sync freeze

dev:
	uvicorn app.main:app --reload

test:
	pytest -v

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

check: lint test

sync:
	python scripts/sync_content.py

freeze:
	uv pip compile pyproject.toml -o requirements.txt
