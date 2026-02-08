import os

# Kafka Config
KAFKA_SERVER = os.getenv("KAFKA_SERVER")
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS").split(",") if os.getenv("KAFKA_TOPICS") else []
KAFKA_GROUP_ID = "worker-group-main"

# Ollama Config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")  # Required

# Worker Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
