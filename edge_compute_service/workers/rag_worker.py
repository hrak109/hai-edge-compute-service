from core.config import KAFKA_SERVER, KAFKA_TOPIC, KAFKA_GROUP_ID, OLLAMA_MODEL, OLLAMA_BASE_URL
from core.kafka_client import create_consumer, create_producer
import logging
import json
import time

# Llama Index
try:
    from llama_index.llms.ollama import Ollama
    from llama_index.core.llms import ChatMessage
except ImportError:
    Ollama = None
    ChatMessage = None
    print("WARNING: llama_index not installed. RAG worker will fail if used.", flush=True)

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

def run_rag_worker():
    print(f"RAG Worker starting for topic: {KAFKA_TOPIC}", flush=True)
    
    consumer = create_consumer(KAFKA_SERVER, KAFKA_TOPIC, KAFKA_GROUP_ID)
    producer = create_producer(KAFKA_SERVER)
    
    current_llm = None
    current_model = None

    for message in consumer:
        try:
            data = message.value
            if not data: continue
            
            question_id = data.get("question_id")
            question_text = data.get("text")
            
            requested_model = data.get("model") or OLLAMA_MODEL
            print(f"RAG: Processing {question_id} with {requested_model}", flush=True)
            
            response = ""
            if requested_model == 'rag-engine':
                response = "RAG support is pending migration."
            else:
                if not Ollama:
                    response = "Error: llama_index not installed."
                else:
                    if current_llm is None or current_model != requested_model:
                        print(f"Initializing Ollama: {requested_model}", flush=True)
                        current_llm = Ollama(
                            model=requested_model,
                            base_url=OLLAMA_BASE_URL,
                            request_timeout=300.0,
                            context_window=4096,
                            additional_kwargs={"num_ctx": 4096}
                        )
                        current_model = requested_model
                    
                    # Log execution details
                    print(f"\n[LLM Execution]", flush=True)
                    print(f"Model Name: {requested_model}", flush=True)
                    print(f"Type: Chat (Ollama)", flush=True)
                    print(f"User Context: {json.dumps(data.get('user_context', {}), indent=2)}", flush=True)
                    print(f"Socius Context: {json.dumps(data.get('socius_context', {}), indent=2)}", flush=True)
                    print(f"Question: {question_text}", flush=True)
                    print(f"--------------------------------------------------\n", flush=True)

                    # Simple chat for now (matching original rag_llm_worker behavior which actually wasn't doing RAG here either!)
                    # The original file imported RAG libs but just called llm.chat in the loop
                    resp_obj = current_llm.chat(
                        messages=[ChatMessage(role="user", content=question_text)]
                    )
                    response = resp_obj.message.content
            
            payload = {
                "question_id": question_id,
                "answer": response,
                "user_id": data.get("user_id"),
                "service": data.get("service"),
                "model": requested_model
            }
            producer.send('answers', value=payload)
            producer.flush()
            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    run_rag_worker()
