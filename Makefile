.PHONY: setup test lint format api dashboard compose-up compose-down migrate load-watchlist

setup:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m ruff format --check .

format:
	python -m ruff check --fix .
	python -m ruff format .

api:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	streamlit run dashboard/Home.py --server.port 8501

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

migrate:
	alembic upgrade head

load-watchlist:
	docker compose run --rm seed
