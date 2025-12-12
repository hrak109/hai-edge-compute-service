import os
import time
import json
import redis

from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.settings import Settings

from rag_engine import RagEngine

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

rag_engine = None

def init_services():
    global rag_engine
    
    # Initialize LLM & Embeddings (Always needed for Ollama)
    Settings.llm = Ollama(
        model=OLLAMA_MODEL, 
        base_url=OLLAMA_BASE_URL, 
        request_timeout=100.0
    )
    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text:latest", 
        base_url=OLLAMA_BASE_URL
    )

    # Initialize RAG Engine only if enabled
    if ENABLE_RAG:
        rag_engine = RagEngine()
    else:
        print("RAG: Disabled via ENABLE_RAG=false. Skipping.", flush=True)

def process_direct_request(question):
    response = Settings.llm.complete(question)
    return str(response)

def main():
    init_services()
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    list_name = os.getenv("REDIS_QUEUE", "questions")
    print(f"Worker listening on queue: {list_name}", flush=True)

    while True:
        item = r.lpop(list_name)
        if item:
            try:
                parts = item.split("|", 2)
                
                if len(parts) == 3:
                    qid, question, params = parts
                    try:
                        domain_params = json.loads(params)
                    except json.JSONDecodeError:
                        domain_params = [params]
                else:
                    qid, question = parts[0], parts[1]
                    domain_params = [] 
                
                answer = process_direct_request(question)

                r.set(f"answer:{qid}", answer)
                
            except Exception as e:
                print(f"Redis Error: {e}", flush=True)
        else:
            time.sleep(3)

if __name__ == "__main__":
    main()