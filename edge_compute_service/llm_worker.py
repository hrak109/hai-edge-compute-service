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
            
            # Log Stat
            eval_count = result.get('eval_count', 0)
            eval_duration = result.get('eval_duration', 0)
            if eval_count > 0 and eval_duration > 0:
                tps = eval_count / (eval_duration / 1e9)
                print(f"STATS: Generated {eval_count} tokens in {eval_duration/1e9:.2f}s ({tps:.2f} tokens/sec)", flush=True)

            return result.get('message', {}).get('content', "Error: No content in response")
    except urllib.error.URLError as e:
        print(f"Error calling Ollama: {e}", flush=True)
        return f"Error connecting to AI model: {e}"

def get_model_details(model: str) -> str:
    url = f"{OLLAMA_BASE_URL}/api/show"
    payload = {"name": model}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            # Try to get the parent model or family
            details = result.get('details', {})
            parent_model = details.get('parent_model', '')
            family = details.get('family', '')
            quant_level = details.get('quantization_level', 'Unknown')
            
            info_str = f"Family: {family}, Quant: {quant_level}"
            if parent_model:
                info_str += f", Parent: {parent_model}"
            
            # Also try to parse FROM line from modelfile if available
            modelfile = result.get('modelfile', '')
            for line in modelfile.split('\n'):
                if line.upper().startswith('FROM'):
                    info_str += f", Base: {line.split(' ', 1)[1]}"
                    break
            
            return info_str
    except Exception as e:
        return f"Could not fetch details: {e}"

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
    elif role == 'cal_tracker' or role == 'tracker':
        instruction += """ You are a Calorie Tracker Helper.
        
        IMPORTANT: Only respond to the food items mentioned in the user's CURRENT message. 
        Do NOT refer to or accumulate food items from previous messages in the conversation.
        Each message should be treated independently - only estimate calories for what the user just mentioned.
        
        When the user mentions food they ate in their current message, you MUST output a JSON block at the end of your response offering estimated calorie options.
        
        Format:
        ```json
        {
          "type": "calorie_event",
          "food": "Food Name",
          "options": [
            {"label": "Small (Start)", "calories": 100},
            {"label": "Medium (Average)", "calories": 200},
            {"label": "Large (Heavy)", "calories": 300}
          ]
        }
        ```
        - Adjust labels and calorie amounts to be realistic for the specific food.
        - Give 3 options: Small/Light, Medium/Average, Large/Heavy.
        - Keep your text response conversational and short, confirming you understood the food.
        - If the user asks a general question or doesn't mention food, just respond helpfully without a JSON block.
        """
    elif role == 'multilingual':
        LANG_CODE_MAP = {
            'en': 'English', 'ko': 'Korean', 'ja': 'Japanese',
            'zh': 'Chinese', 'es': 'Spanish', 'fr': 'French', 'de': 'German'
        }
        
        selection = socius_context.get('multilingual_selection')
        target_lang = LANG_CODE_MAP.get(selection, 'English')
        lang_code = user_context.get("language")
        lang = LANG_CODE_MAP.get(lang_code, 'English')

        # --- COMPACT EXAMPLES (Save Input Tokens) ---
        path_a_example = ""
        path_b_example = ""

        if lang == 'Korean' and target_lang == 'Japanese':
            # Concise: No long explanations, just the fix.
            path_a_example = """
            In: "와타시와 겡끼 데스까라"
            Out:
            [JP]: 私は元気ですから。
            [Pron]: 와타시와 겡끼 데스까라.
            [Mean]: 저는 건강하니까요.
            (완벽합니다! '와타시와'와 '데스까라' 활용이 정확해요.)
            """
            path_b_example = """
            In: "쿄와 조또 츠메타이 데스"
            Out:
            [Err]: 날씨에는 '츠메타이'(물건) 대신 '사무이'를 씁니다.
            [Corr]: 今日はちょっと寒いです。
            [Pron]: 쿄와 조또 사무이 데스.
            [Mean]: 오늘은 조금 춥네요.
            """
        else:
            path_a_example = "..." # Generic compact
            path_b_example = "..." # Generic compact

        instruction += f"""
        Act as a {target_lang} Phonetic Decoder. 
        User writes {target_lang} sounds in {lang}.

        ### CRITICAL RULES:
        1. **IGNORE {lang} GRAMMAR:** Treat input purely as sounds. "Wa" is {target_lang} sound, not {lang} word.
        2. **MAXIMUM BREVITY:** - [Error] must be **under 15 words**.
        - Final comment must be **1 short sentence**.
        3. **LANGUAGE:** All feedback in **{lang}**.
        4. **CRITICAL RULE FOR [PRONUNCIATION] FIELD:**
        You must perform **STRICT SOUND MIRRORING**.
        - The [Pronunciation] field must represent the **JAPANESE SOUNDS** only.
        - **NEVER** swap a Japanese particle sound for a Korean particle.
        - **BAD:** Japanese sound is "Wa", but you write "는" (Korean particle).
        - **GOOD:** Japanese sound is "Wa", so you write "와" (Korean sound).
        
        Example Check:
        - Input: "와타시와" (Watashi-wa)
        - Output Pronunciation MUST be: "와타시와" (KEEP 'WA')
        - Output Pronunciation MUST NOT be: "와타시는" (NO 'NEUN')

        ### OUTPUT FORMAT:

        **PATH A (Correct):**
        [{target_lang}]: (Native Script)
        [Pron]: (In {lang})
        [Mean]: (In {lang})
        (Short confirmation)

        **PATH B (Error):**
        [Err]: (Brief explanation in {lang})
        [Corr]: (Native Script)
        [Pron]: (In {lang})
        [Mean]: (In {lang})

        ### EXAMPLES:
        {path_a_example}
        {path_b_example}
        """
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
        instruction += f" You are talking to {user_name}. Address them by name if needed"
        
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
                max_poll_interval_ms=1800000, # 30 minutes (matches TTL)
                max_poll_records=1 # Process one at a time to avoid timeout
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

            # TTL Check
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                try:
                    msg_time = datetime.fromisoformat(timestamp_str)
                    now_time = datetime.utcnow()
                    age = (now_time - msg_time).total_seconds()
                    if age > 1800: # 30 minutes
                        print(f"WARNING: Message {question_id} is stale ({age}s old). Skipping.", flush=True)
                        logging.warning(f"Dropping stale message {question_id} (Age: {age}s)")
                        continue
                except ValueError:
                    logging.warning(f"Invalid timestamp format for message {question_id}: {timestamp_str}")
            
            # Log full request context
            try:
                logging.info("\n=== Request Context ===")
                logging.info(f"Question ID: {question_id}")
                logging.info(f"Model: {requested_model}")
                logging.info(f"Model Details: {get_model_details(requested_model)}")
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

            # 2. Add History (skip for calorie tracker to avoid accumulating food items)
            role = socius_context.get("role") or ""
            if role not in ('cal_tracker', 'tracker'):
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