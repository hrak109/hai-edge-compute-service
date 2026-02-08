from core.config import KAFKA_SERVER, KAFKA_TOPICS, KAFKA_GROUP_ID, OLLAMA_MODEL
from core.kafka_client import create_consumer, create_producer
from services.llm import query_ollama
from services import prompts_socius, prompts_context_ai
import logging
from datetime import datetime, timezone
import json
import time  # noqa: F401
import re  # noqa: F401

try:
    from services.rag_engine import RagEngine
except ImportError:
    RagEngine = None
    print("WARNING: Could not import RagEngine. RAG features will be disabled.", flush=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)


def run_worker():
    print(f"Standard Worker starting for topics: {KAFKA_TOPICS}", flush=True)

    consumer = create_consumer(KAFKA_SERVER, KAFKA_TOPICS, KAFKA_GROUP_ID)
    producer = create_producer(KAFKA_SERVER)

    # Initialize RAG Engine if enabled or potentially needed
    rag_engine = None
    if RagEngine:
        try:
            rag_engine = RagEngine()
        except Exception as e:
            print(f"Failed to initialize RAG Engine: {e}", flush=True)

    print(f"Worker listening on topics: {KAFKA_TOPICS}", flush=True)

    for message in consumer:
        try:
            data = message.value
            if not data:
                continue

            # Identify source topic
            source_topic = message.topic

            question_id = data.get("question_id")
            question_text = data.get("text")
            # history = data.get("history") or []
            user_context = data.get("user_context") or {}
            socius_context = data.get("socius_context") or {}
            message_group_id = data.get("message_group_id")

            requested_model = data.get("model") or OLLAMA_MODEL

            print(f"DEBUG: Processing question ID: {question_id} Group ID: {message_group_id} "
                  f"Model: {requested_model} Topic: {source_topic}", flush=True)

            # TTL Check
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                try:
                    msg_time = datetime.fromisoformat(timestamp_str)
                    if msg_time.tzinfo is None:
                        msg_time = msg_time.replace(tzinfo=timezone.utc)
                    now_time = datetime.now(timezone.utc)
                    age = (now_time - msg_time).total_seconds()
                    if age > 1800:  # 30 minutes
                        logging.warning(f"Dropping stale message {question_id} (Age: {age}s)")
                        continue
                except (ValueError, TypeError) as e:
                    logging.warning(f"Time parsing error for message {question_id}: {e}")

            # Logic Routing
            response = ""

            # Case 1: RAG Request
            if source_topic == 'questions-rag':
                if not rag_engine:
                    response = "Error: RAG Engine is not available on this worker."
                else:
                    # Extract Auth Params/ACL from context if needed
                    # For now passing "public" or user_id as a placeholder for ACL
                    auth_param = f"user_{data.get('user_id')}"
                    if not data.get('user_id'):
                        auth_param = "public"

                    print(f"RAG Query: {question_text} (Auth: {auth_param})", flush=True)
                    try:
                        response = rag_engine.process_request(question_text, auth_param)
                    except Exception as re_err:
                        print(f"RAG Error: {re_err}", flush=True)
                        response = "Error processing RAG request."

            # Case 2: Standard LLM Request
            else:
                # Log full request context
                try:
                    logging.info("\n=== LLM Execution ===")
                    logging.info(f"Model Name: {requested_model}")
                    logging.info("Type: Chat (Standard)")
                    logging.info(f"User Context:\n{json.dumps(user_context, indent=2, ensure_ascii=False)}")
                    logging.info(f"Socius Context:\n{json.dumps(socius_context, indent=2, ensure_ascii=False)}")
                    logging.info(f"Question: {question_text}")
                    logging.info("=======================\n")
                except Exception as e:
                    print(f"Error logging request: {e}", flush=True)

                # Determine System Instruction based on Topic/Service
                system_instruction = ""

                if source_topic == 'questions-context-ai':
                    # Context AI (e.g. Oakhill Pines)
                    system_instruction = prompts_context_ai.get_system_instruction()
                else:
                    # Default / Socius Friends
                    system_instruction = prompts_socius.get_system_instruction(user_context, socius_context)

                # DEBUG info about prompt source
                if hasattr(prompts_context_ai, 'HAS_SECRET'):
                    logging.info(f"Context AI Secret Mode: {prompts_context_ai.HAS_SECRET}")
                if hasattr(prompts_socius, 'HAS_SECRET'):
                    logging.info(f"Socius Secret Mode: {prompts_socius.HAS_SECRET}")

                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})

                # Format user input (e.g. for Multilingual role wrapping)
                formatted_question = prompts_socius.format_user_input(user_context, socius_context, question_text)

                messages.append({"role": "user", "content": formatted_question})

                response = query_ollama(requested_model, messages)

            result_payload = {
                "question_id": question_id,
                "answer": response,
                "user_id": data.get("user_id"),
                "service": data.get("service"),
                "model": requested_model,
                "message_group_id": message_group_id
            }

            producer.send('answers', value=result_payload)
            producer.flush()

            print(f"Answered: {question_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}", flush=True)
            # time.sleep(1) # Prevent tight loop on error?


if __name__ == "__main__":
    run_worker()
