.PHONY: dev dev-js build-js test lint check sync freeze help

dev:
	uvicorn app.main:app --reload

dev-js:
	cd frontend && bun run build --watch

build-js:
	cd frontend && bun run build

test:
	pytest -v

lint:
	ruff check app/ tests/
	ruff format app/ tests/

lint-scripts:
	ruff check scripts/
	ruff format scripts/

check: lint test

sync:
	python scripts/sync_content.py

freeze:
	uv pip compile pyproject.toml -o requirements.txt

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  dev      Start Python dev server with hot reload"
	@echo "  dev-js   Watch and rebuild frontend (run alongside dev)"
	@echo "  build-js Build frontend bundle for production"
	@echo "  test     Run pytest"
	@echo "  lint     Run ruff linter and auto-format"
	@echo "  check    Run lint + test"
	@echo "  sync     Sync content from S3"
	@echo "  freeze   Generate requirements.txt from pyproject.toml"
	@echo "  help     Show this help message"
