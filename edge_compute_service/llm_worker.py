import os
import time
import json
import redis

from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.settings import Settings
from llama_index.core.llms import ChatMessage

from rag_engine import RagEngine

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

rag_engine = None

def init_services():
    global rag_engine
    
    # Settings.llm removed - we instantiate per-request now.

    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text:latest", 
        base_url=OLLAMA_BASE_URL
    )

    # Initialize RAG Engine
    # Deactivated for now
    # try:
    #     rag_engine = RagEngine()
    # except Exception as e:
    #     print(f"Failed to initialize RAG Engine: {e}. RAG will be disabled.", flush=True)
    #     rag_engine = None
    rag_engine = None

def process_direct_request(question):
    response = Settings.llm.complete(question)
    return str(response)

def main():
    init_services()
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    list_name = os.getenv("REDIS_QUEUE", "questions")
    print(f"Worker listening on queue: {list_name}", flush=True)

    # Caching functionality to support "sticky" sessions per model
    # while allowing reset when switching models.
    current_llm = None
    current_model = None

    while True:
        item = r.lpop(list_name)
        if item:
            try:
                parts = item.split("|")
                if len(parts) == 3:
                     # Format: id|text|model
                    question_id, question_text, requested_model = parts
                else:
                    print(f"Invalid message format: {item}", flush=True)
                    continue
                    
                print(f"Processing question ID: {question_id} with model: {requested_model}", flush=True)

                if requested_model == 'rag-engine':
                    if rag_engine:
                         response = rag_engine.query(question_text)
                    else:
                         response = "Error: RAG Engine is not initialized."
                else:
                    # Check if we need to switch models (or init for the first time)
                    if current_llm is None or current_model != requested_model:
                        print(f"Initializing new LLM instance for model: {requested_model}", flush=True)
                        current_llm = Ollama(
                            model=requested_model,
                            base_url=OLLAMA_BASE_URL,
                            request_timeout=100.0
                        )
                        current_model = requested_model
                
                    response = current_llm.chat(
                        messages=[ChatMessage(role="user", content=question_text)]
                    ).message.content

                r.set(f"answer:{question_id}", response)
                # Set TTL to 1 hour to prevent clutter
                r.expire(f"answer:{question_id}", 3600)
                
                print(f"Answered: {question_id}", flush=True)

            except Exception as e:
                print(f"Error processing message: {e}", flush=True)
        else:
            time.sleep(3)

if __name__ == "__main__":
    main()