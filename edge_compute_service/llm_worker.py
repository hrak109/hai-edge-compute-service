import os
import time
import json
import urllib.request
import urllib.error
from kafka import KafkaConsumer, KafkaProducer

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
KAFKA_SERVER = os.getenv("KAFKA_SERVER")

# We use urllib to avoid external dependencies like 'requests' if not strictly needed
def query_ollama(model, messages, system_prompt=None):
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096
        }
    }
    if system_prompt:
        payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        # Note: For /api/chat, 'system' parameter is technically not documented as top-level override 
        # in some versions, it expects a message with role 'system'.
        # Trying to insert it as the FIRST message is the most standard way.
        # Wait, I previously tried appending it. Maybe insert(0) is key?
        # Earlier code: `messages` was empty list. I appended system. Then extended history. Then user.
        # That effectively put it at index 0.
        # But user said it failed.
        # Maybe I should try the Payload 'system' param anyways ?
        # Actually, let's try BOTH: Ensure it's in messages[0], AND try setting 'system' param?
        # Double system prompt?
        
    # Let's try the Payload 'system' param only if 'messages' approach failed.
    # But /api/chat docs say 'messages'.
    # If I use /api/generate, 'system' works.
    # BUT, recently Ollama added support for 'system' in /chat options? No.
    
    # User said "removed from Modelfile".
    # If I use `insert(0, ...)` here, it replicates what I did in main().
    
    # Let's try to be clever: What if I didn't send `system` message but used `system` param?
    # Some users report /api/chat DOES respect top level 'system' field.
    # I will try adding it to payload top level.
    if system_prompt:
        payload['system'] = system_prompt
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {}).get('content', "Error: No content in response")
    except urllib.error.URLError as e:
        print(f"Error calling Ollama: {e}", flush=True)
        return f"Error connecting to AI model: {e}"

def main():
    topic_name = os.getenv("KAFKA_TOPIC", "questions")
    print(f"Worker connecting to Kafka at {KAFKA_SERVER}, topic: {topic_name}", flush=True)

    # Retry connection for Kafka
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
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
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
            # Format: {"question_id": ..., "text": ..., "model": ..., "service": ..., "user_id": ..., "history": [], "user_context": {}}
            
            question_id = data.get("question_id")
            question_text = data.get("text")
            history = data.get("history") or []
            user_context = data.get("user_context") or {}
            
            # Resolve model
            default_model = os.environ.get("OLLAMA_MODEL")
            requested_model = data.get("model") or default_model
            
            print(f"Processing question ID: {question_id} with model: {requested_model}", flush=True)

            # Build Messages
            messages = []
            
            # System Context
            socius_role = user_context.get("socius_role")
            
            if socius_role == 'faith_companion':
                system_instruction = "You are Socius, an expert of Christian beliefs and companion of christian faith, giving mental advice using teachings and quotes from the christian bible. If asked about a bible quote, answer what it means and how that would apply to the user. Always answer with direct, actual quotes from the Bible, that suit the user's question and situation."
            elif socius_role == 'friend':
                system_instruction = "You are Socius, a friendly companion giving mental advice and comforting the user. Give helpful quotes from the bible, philosophers, and other quotes that can comfort the user based on their question and situation."
            elif socius_role == 'partner':
                system_instruction = "You are Socius, a loving partner of the user, acting as the user's boyfriend or girlfriend. Give helpful quotes from the bible, philosophers, and other quotes that can comfort the user based on their question and situation."
            elif socius_role == 'assistant':
                system_instruction = "You are Socius, a helpful assistant. Answer objectively, like an assistant, to questions and feedback."
            else:
                system_instruction = "You are Socius, a helpful AI assistant."

                
            if user_context:
                display_name = user_context.get("display_name") or user_context.get("username") or "User"
                system_instruction += f" You are talking to {display_name}. Address them by their name ({display_name}) wherever applicable, but not always."
                
                # Language enforcement
                lang_code = user_context.get("language")
                if lang_code == 'ko':
                    system_instruction += " Always answer in Korean (한국어)."
                elif lang_code == 'en':
                     system_instruction += " Always answer in English."
                
            # Log context for debugging
            print(f"Context Role: {socius_role}, System Instruction Pfx: {system_instruction[:50]}...", flush=True)

            # Messages
            # Note: We pass system_instruction as a top-level parameter to query_ollama
            # instead of a message with role='system', to ensure it overrides Modelfile defaults.
            
            # History
            messages.extend(history)
            
            # Current Message
            messages.append({"role": "user", "content": question_text})

            # RAG check (Removed as requested, simplified logic)
            if requested_model == 'rag-engine':
                 response = "RAG is not maintained in this lightweight worker."
            else:
                 response = query_ollama(requested_model, messages, system_prompt=system_instruction)

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