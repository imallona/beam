.PHONY: help install install-all test test-r lint fmt vignettes docs clean

help:
	@echo "Available targets:"
	@echo "  install      Install with [dev] extras (lint + pytest)"
	@echo "  install-all  Install with [dev,docs,io] extras (full local dev environment)"
	@echo "  test         Run the Python test suite (pytest)"
	@echo "  test-r       Run the R-side metric card validation (needs Rscript)"
	@echo "  lint         Run ruff check"
	@echo "  fmt          Run ruff format"
	@echo "  vignettes    Render the Quarto vignettes under examples/"
	@echo "  docs         Render the full Quarto site (vignettes + explanations + ADRs)"
	@echo "  clean        Remove build artefacts, caches, and rendered docs"

install:
	python -m pip install -e ".[dev]"

install-all:
	python -m pip install -e ".[dev,docs,io]"

test:
	pytest -q

test-r:
	Rscript tests/validate_cards.R

lint:
	ruff check .

fmt:
	ruff format .

vignettes:
	quarto render examples/

docs:
	quarto render

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ docs/_site/ _site/
	find examples/ -type f \( -name '*.html' -o -name '*_files' \) -exec rm -rf {} +
	find . -type d -name __pycache__ -exec rm -rf {} +
