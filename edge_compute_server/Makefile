.PHONY: up down build logs restart run-worker run-infra setup-models test setup-local

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

restart:
	docker compose down && docker compose up -d --build

run-worker:
	docker compose up -d --build llm_worker_main

test:
	./venv/bin/python -m pytest

setup-local:
	python3 -m venv venv && \
	. venv/bin/activate && \
	pip install -r requirements.txt

setup-model:
	@echo "Creating SOC Model..."
	docker exec ollama_container ollama create soc-model -f /root/Modelfiles/soc-Modelfile.txt
	@echo "Models created successfully!"