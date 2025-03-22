.PHONY: install test lint fmt docs clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

docs:
	quarto render

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ docs/_site/
	find . -type d -name __pycache__ -exec rm -rf {} +
