import os
import time
import json
import urllib.request
import urllib.error
from kafka import KafkaConsumer, KafkaProducer
import logging
from datetime import datetime

# Configure logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

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


def get_system_instruction(user_context: dict, socius_context: dict) -> str:
    # 1. Determine Role and Attributes
    role = socius_context.get("role") or "casual"
    bot_name = socius_context.get("display_name") or "Socius"
    tone = socius_context.get("tone") or "friendly"
    intimacy = socius_context.get("intimacy_level") or 5
    
    # Base Instruction
    instruction = f"You are {bot_name}, a {role}."
    
    # 2. Add Role-Specific Context
    if role == 'christian':
        instruction += " You are an expert of Christian beliefs, and a good friend giving mental advice and consoling using teachings and quotes from the christian bible. If asked about a bible quote, explain in detail and how that would apply to the user."
    elif role == 'casual':
        instruction += " You are a casual friend of the user, casually talking, asking, and answering questions."
    elif role == 'multilingual':
        target_lang = socius_context.get('multilingual_selection', 'the language user speaks')
        lang_code = user_context.get("language")
        if lang_code == 'ko':
            lang = "한국어"
        elif lang_code == 'en':
            lang = "English"
        instruction += f" You are a multilingual friend of the user, speaking {target_lang}. Write short and simple answers, and always answer in 3 paragraphs: 1 paragraph in {target_lang}, 1 paragraph of {target_lang} pronunciation written in {lang}, and 1 paragraph with translation in {lang}. If user makes any language error or mistake in message, correct it and write back asking if that's what they've meant. Only if user's message is correct, provide answer to their questions using the 3 paragraphs format"
    elif role == 'cal_tracker':
        instruction += " You are a calorie tracking friend. When the user provides description of what they ate, give rough estimate of the calories they ate. If not descriptive enough, ask them for more clarification."
    elif role == 'romantic':
        instruction += " You are a loving partner of the user. Be affectionate and supportive. Use emojis"
    elif role == 'assistant':
        instruction += " Answer objectively and helpfully to questions and feedback."
    elif role == 'workout':
        instruction += " You are a workout tracking friend of the user. When the user provides description of what they did, give rough estimate of the calories they burned. If not descriptive enough, ask them for more clarification."
    elif role == 'secrets':
        instruction += " You are a password and secrets keeper friend of the user. When the user provides password or secrets, format it to user name and password and keep it secret and safe."
    else:
        instruction += " You are Socius, a helpful AI assistant."

    # 3. Add Tone and Intimacy
    if tone == 'formal':
        instruction += " You should speak in a formal tone. If user writes in Korean, use 존댓말"
    elif role == 'casual':
        instruction += " You should speak in a casual tone. If user writes in Korean, use 반말"

    if intimacy:
        instruction += f" Your intimacy level with the user is {intimacy}/7 (7 being closest)."

    # 4. Add User Context
    if user_context:
        user_name = user_context.get("display_name") or user_context.get("user_uid") or "User"
        instruction += f" You are talking to {user_name}. Address them by name occasionally."
        
        lang_code = user_context.get("language")
        if lang_code == 'ko':
            instruction += "한국어로 대화해."
        elif lang_code == 'en':
             instruction += "Answer in English."
    
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
            socius_context = data.get("socius_context") or {} # NEW: Get Socius Context
            
            default_model = os.environ.get("OLLAMA_MODEL")
            requested_model = data.get("model") or default_model
            
            print(f"DEBUG: Processing question ID: {question_id} Context: {data.get('context')} Model: {requested_model}", flush=True)
            
            # Log full request context
            try:
                logging.info("\n=== Request Context ===")
                logging.info(f"Question ID: {question_id}")
                logging.info(f"Model: {requested_model}")
                logging.info(f"Socius Context:\n{json.dumps(socius_context, indent=2, ensure_ascii=False)}")
                logging.info(f"User Context:\n{json.dumps(user_context, indent=2, ensure_ascii=False)}")
                logging.info(f"Question Text: {question_text}")
                logging.info("=======================\n")
            except Exception as e:
                print(f"Error logging request: {e}", flush=True)

            system_instruction = get_system_instruction(user_context, socius_context)

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
                "model": requested_model,
                "context": data.get("context") # return context
            }
            
            print(f"DEBUG: Sending answer payload: {json.dumps(result_payload)}", flush=True)
            producer.send('answers', value=result_payload)
            producer.flush()
            
            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}", flush=True)

if __name__ == "__main__":
    main()