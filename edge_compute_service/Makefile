.PHONY: up down build logs restart run-ohp run-private run-socius run-infra

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

# Selective Run Targets
# These commands automatically start dependencies (ollama, kafka-tunnel, etc.)
run-ohp:
	docker compose up -d llm_worker_oakhillpines

run-private:
	docker compose up -d llm_worker_private

run-socius:
	docker compose up -d llm_worker_socius

run-infra:
	docker compose up -d ollama kafka-tunnel weaviate

setup-models:
	@echo "Creating OHP Model..."
	docker exec ollama_container ollama create ohp-llama3.2:3b -f /root/Modelfiles/ohp-Modelfile.txt
	@echo "Creating HBB Model..."
	docker exec ollama_container ollama create hbb-llama3.2:3b -f /root/Modelfiles/hbb-Modelfile.txt
	@echo "Models created successfully!"
