from core.config import KAFKA_SERVER, KAFKA_TOPIC, KAFKA_GROUP_ID, OLLAMA_MODEL
from core.kafka_client import create_consumer, create_producer
from services.llm import query_ollama, get_model_details
from services.prompts import get_system_instruction
import logging
from datetime import datetime, timezone
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def run_worker():
    print(f"Standard Worker starting for topic: {KAFKA_TOPIC}", flush=True)
    
    consumer = create_consumer(KAFKA_SERVER, KAFKA_TOPIC, KAFKA_GROUP_ID)
    producer = create_producer(KAFKA_SERVER)
    
    print(f"Worker listening on topic: {KAFKA_TOPIC}", flush=True)

    for message in consumer:
        try:
            data = message.value
            if not data:
                continue
            
            question_id = data.get("question_id")
            question_text = data.get("text")
            history = data.get("history") or []
            user_context = data.get("user_context") or {}
            socius_context = data.get("socius_context") or {}
            
            requested_model = data.get("model") or OLLAMA_MODEL
            
            print(f"DEBUG: Processing question ID: {question_id} Context: {data.get('context')} Model: {requested_model}", flush=True)

            # TTL Check
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                try:
                    msg_time = datetime.fromisoformat(timestamp_str)
                    now_time = datetime.now(timezone.utc)
                    age = (now_time - msg_time).total_seconds()
                    if age > 1800: # 30 minutes
                        logging.warning(f"Dropping stale message {question_id} (Age: {age}s)")
                        continue
                except ValueError:
                    logging.warning(f"Invalid timestamp format for message {question_id}: {timestamp_str}")
            
            # Log full request context
            try:
                logging.info("\n=== LLM Execution ===")
                logging.info(f"Model Name: {requested_model}")
                logging.info(f"Type: Chat (Standard)")
                try:
                     details = get_model_details(requested_model)
                     logging.info(f"Model Details: {details}")
                except:
                     logging.info("Model Details: Unavailable")
                     
                logging.info(f"User Context:\n{json.dumps(user_context, indent=2, ensure_ascii=False)}")
                logging.info(f"Socius Context:\n{json.dumps(socius_context, indent=2, ensure_ascii=False)}")
                logging.info(f"Question: {question_text}")
                logging.info("=======================\n")
            except Exception as e:
                print(f"Error logging request: {e}", flush=True)

            system_instruction = get_system_instruction(user_context, socius_context)
            messages = []
            if system_instruction:
                 messages.append({"role": "system", "content": system_instruction})

            # History is currently disabled based on original code 'if False:'
            # if role not in ('cal_tracker', 'tracker'): messages.extend(history)
            
            messages.append({"role": "user", "content": question_text})
            
            if requested_model == 'rag-engine':
                 response = "RAG is not maintained in this lightweight worker."
            else:
                 response = query_ollama(requested_model, messages)

            result_payload = {
                "question_id": question_id,
                "answer": response,
                "user_id": data.get("user_id"),
                "service": data.get("service"),
                "model": requested_model,
                "context": data.get("context")
            }
            
            # print(f"DEBUG: Sending answer payload: {json.dumps(result_payload)}", flush=True)
            producer.send('answers', value=result_payload)
            producer.flush()
            
            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}", flush=True)
            # time.sleep(1) # Prevent tight loop on error?

if __name__ == "__main__":
    run_worker()
