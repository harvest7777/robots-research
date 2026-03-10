.PHONY: test lint check

test:
	pytest

lint:
	lint-imports

check: lint test
