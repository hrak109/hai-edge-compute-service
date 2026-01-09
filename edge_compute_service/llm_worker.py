import os
import time
import json
import urllib.request
import urllib.error
from kafka import KafkaConsumer, KafkaProducer

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
KAFKA_SERVER = os.getenv("KAFKA_SERVER")

def query_ollama(model: str, messages: list[dict]) -> str:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {}).get('content', "Error: No content in response")
    except urllib.error.URLError as e:
        print(f"Error calling Ollama: {e}", flush=True)
        return f"Error connecting to AI model: {e}"

def safe_json_deserializer(x: bytes) -> dict | None:
    try:
        return json.loads(x.decode('utf-8'))
    except Exception as e:
        print(f"Skipping malformed message: {e}", flush=True)
        return None

def get_system_instruction(user_context: dict) -> str:
    socius_role = user_context.get("socius_role")
    
    if socius_role == 'faith_companion':
        instruction = "You are Socius, an expert of Christian beliefs and companion of christian faith, giving mental advice using teachings and quotes from the christian bible. If asked about a bible quote, answer what it means and how that would apply to the user. Always answer with direct, actual quotes from the Bible, that suit the user's question and situation."
    elif socius_role == 'friend':
        instruction = "You are Socius, a friendly companion giving mental advice and comforting the user. Give helpful quotes from the bible, philosophers, and other quotes that can comfort the user based on their question and situation."
    elif socius_role == 'partner':
        instruction = "You are Socius, a loving partner of the user, acting as the user's boyfriend or girlfriend. Give helpful quotes from the bible, philosophers, and other quotes that can comfort the user based on their question and situation."
    elif socius_role == 'assistant':
        instruction = "You are Socius, a helpful assistant. Answer objectively, like an assistant, to questions and feedback."
    else:
        instruction = "You are Socius, a helpful AI assistant."

    if user_context:
        display_name = user_context.get("display_name") or user_context.get("username") or "User"
        instruction += f" You are talking to {display_name}. Address them by their name ({display_name}) wherever applicable, but not always."
        
        lang_code = user_context.get("language")
        if lang_code == 'ko':
            instruction += " Always answer in Korean (한국어)."
        elif lang_code == 'en':
             instruction += " Always answer in English."
    
    return instruction

def main() -> None:
    topic_name = os.getenv("KAFKA_TOPIC", "questions")
    print(f"Worker connecting to Kafka at {KAFKA_SERVER}, topic: {topic_name}", flush=True)

    consumer = None
    producer = None
    while True:
        try:
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers=[KAFKA_SERVER],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=f"worker-group-{topic_name}",
                value_deserializer=safe_json_deserializer,
                max_poll_interval_ms=600000 
            )
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_SERVER],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            print("Kafka connected successfully.", flush=True)
            break
        except Exception as e:
            print(f"Searching for Kafka... {e}", flush=True)
            time.sleep(5)
            
    print(f"Worker listening on topic: {topic_name}", flush=True)

    for message in consumer:
        try:
            data = message.value
            if not data:
                continue
            
            question_id = data.get("question_id")
            question_text = data.get("text")
            history = data.get("history") or []
            user_context = data.get("user_context") or {}
            
            default_model = os.environ.get("OLLAMA_MODEL")
            requested_model = data.get("model") or default_model
            
            print(f"Processing question ID: {question_id} with model: {requested_model}", flush=True)

            system_instruction = get_system_instruction(user_context)

            messages = []
            
            # 1. Add System Instruction as the FIRST message with role 'system'
            if system_instruction:
                 messages.append({"role": "system", "content": system_instruction})

            # 2. Add History
            messages.extend(history)
            
            # 3. Add Current Question
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
                "model": requested_model
            }
            
            producer.send('answers', value=result_payload)
            producer.flush()
            
            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}", flush=True)

if __name__ == "__main__":
    main()