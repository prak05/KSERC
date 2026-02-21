.PHONY: install run test lint format build docker-run

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

lint:
	black --check .
	isort --check-only .
	flake8

format:
	black .
	isort .

build:
	docker build -t kserc-ara-backend .

docker-run:
	docker-compose up --build
