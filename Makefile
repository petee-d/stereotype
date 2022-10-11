.DEFAULT_GOAL := pr

.PHONY: install
install:
	pip install -r requirements_dev.txt
	pip install -r docs/requirements.txt

.PHONY: lint
lint:
	# Errors
	flake8 stereotype tests examples --count --select=E9,F63,F7,F82 --show-source --statistics
	# Warnings
	flake8 stereotype tests examples --count --exit-zero --max-complexity=15 --max-line-length=120 --statistics

.PHONY: test
test:
	pytest

.PHONY: test-coverage
test-coverage:
	coverage run -m pytest

.PHONY: pr
pr: lint test-coverage

.PHONY: docs
docs:
	sphinx-build -M clean docs docs/_build
	sphinx-build -M html docs docs/_build
