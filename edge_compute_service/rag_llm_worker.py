import os
import time
import json
from kafka import KafkaConsumer, KafkaProducer

from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.settings import Settings
from llama_index.core.llms import ChatMessage

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

def init_services():
    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text:latest", 
        base_url=OLLAMA_BASE_URL
    )

def main():
    init_services()
    
    kafka_server = os.getenv("KAFKA_SERVER", "kafka-tunnel:9092")
    topic_name = os.getenv("KAFKA_TOPIC", "questions")
    
    print(f"Worker connecting to Kafka at {kafka_server}, topic: {topic_name}", flush=True)

    # Retry connection
    while True:
        try:
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers=[kafka_server],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f"worker-group-{topic_name}",
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                max_poll_interval_ms=600000 # 10 minutes for slow inference
            )
            producer = KafkaProducer(
                bootstrap_servers=[kafka_server],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            break
        except Exception as e:
            print(f"Searching for Kafka... {e}", flush=True)
            time.sleep(5)
            
    print(f"Worker listening on topic: {topic_name}", flush=True)

    current_llm = None
    current_model = None

    for message in consumer:
        try:
            data = message.value
            # Format: {"question_id": ..., "text": ..., "model": ..., "service": ..., "user_id": ...}
            
            question_id = data.get("question_id")
            question_text = data.get("text")
            # Use payload model, or fallback to env var
            default_model = os.environ["OLLAMA_MODEL"]
            requested_model = data.get("model") or default_model
            
            print(f"Processing question ID: {question_id} with model: {requested_model}", flush=True)

            if requested_model == 'rag-engine':
                response = "RAG not supported in this migration yet."
            else:
                if current_llm is None or current_model != requested_model:
                    print(f"Initializing new LLM instance for model: {requested_model}", flush=True)
                    current_llm = Ollama(
                        model=requested_model,
                        base_url=OLLAMA_BASE_URL,
                        request_timeout=300.0,
                        context_window=4096,
                        additional_kwargs={"num_ctx": 4096}
                    )
                    current_model = requested_model
            
                response_obj = current_llm.chat(
                    messages=[ChatMessage(role="user", content=question_text)]
                )
                response = response_obj.message.content

            # Send answer
            result_payload = {
                "question_id": question_id,
                "answer": response,
                "user_id": data.get("user_id"),
                "service": data.get("service"),
                "model": requested_model
            }
            
            producer.send('answers', value=result_payload)
            producer.flush()
            
            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}", flush=True)

if __name__ == "__main__":
    main()