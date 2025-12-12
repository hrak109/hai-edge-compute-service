.PHONY: up down build logs restart

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

setup-models:
	@echo "Creating OHP Model..."
	docker exec ollama_container ollama create ohp-llama3.2:3b -f /root/Modelfiles/ohp-Modelfile.txt
	@echo "Creating HBB Model..."
	docker exec ollama_container ollama create hbb-llama3.2:3b -f /root/Modelfiles/hbb-Modelfile.txt
	@echo "Models created successfully!"
