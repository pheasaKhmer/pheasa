.PHONY: check lint format test validate

check: lint test validate

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

validate:
	uv run python scripts/check_attribution.py
	uv run python scripts/validate_manifest.py
	uv run python scripts/validate_items.py
