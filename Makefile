.PHONY: dev test lint check sync freeze help

dev:
	uvicorn app.main:app --reload

test:
	pytest -v

lint:
	ruff check app/ tests/
	ruff format app/ tests/

check: lint test

sync:
	python scripts/sync_content.py

freeze:
	uv pip compile pyproject.toml -o requirements.txt

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  dev      Start development server with hot reload"
	@echo "  test     Run pytest"
	@echo "  lint     Run ruff linter and auto-format"
	@echo "  check    Run lint + test"
	@echo "  sync     Sync content from S3"
	@echo "  freeze   Generate requirements.txt from pyproject.toml"
	@echo "  help     Show this help message"
