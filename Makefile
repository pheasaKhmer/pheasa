.PHONY: check lint format test validate bench

check: lint test validate bench

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
	uv run python scripts/validate_golden.py

bench:
	uv run python scripts/bench_throughput.py --check
