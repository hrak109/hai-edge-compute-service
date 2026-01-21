import os

# Kafka Config
KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "questions")
KAFKA_GROUP_ID = f"worker-group-{KAFKA_TOPIC}"

# Ollama Config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") # Required

# Worker Config
ENABLE_RAG = os.getenv("ENABLE_RAG", "False").lower() in ('true', '1', 't')
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
