POETRY ?= poetry
RUFF ?= $(POETRY) run ruff
MYPY ?= $(POETRY) run mypy
PYTEST ?= $(POETRY) run pytest
PRETTIER ?= npx prettier

.PHONY: check lint format format-check format-js-check typecheck test docker-up docker-down

check: lint format-check format-js-check typecheck test

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
	$(RUFF) check --fix .
	$(PRETTIER) --write "combinario/**/*.{js,html,css}"

format-check:
	$(RUFF) format --check .

format-js-check:
	$(PRETTIER) --check "combinario/**/*.{js,html,css}"

typecheck:
	$(MYPY) combinario tests

test:
	$(PYTEST)

docker-up:
	docker compose up --build

docker-down:
	docker compose down
