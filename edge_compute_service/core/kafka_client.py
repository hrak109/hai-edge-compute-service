from kafka import KafkaConsumer, KafkaProducer
import json
import time
from typing import Callable, Any

def safe_json_deserializer(x: bytes) -> dict | None:
    try:
        return json.loads(x.decode('utf-8'))
    except Exception as e:
        print(f"Skipping malformed message: {e}", flush=True)
        return None

def create_consumer(server: str, topic: str, group_id: str) -> KafkaConsumer:
    while True:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[server],
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=safe_json_deserializer,
                max_poll_interval_ms=1800000, # 30 minutes
                max_poll_records=1
            )
            print(f"Kafka Consumer connected to {server}/{topic}", flush=True)
            return consumer
        except Exception as e:
            print(f"Waiting for Kafka ({server})... {e}", flush=True)
            time.sleep(5)

def create_producer(server: str) -> KafkaProducer:
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[server],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            print("Kafka Producer connected.", flush=True)
            return producer
        except Exception as e:
             print(f"Waiting for Kafka Producer ({server})... {e}", flush=True)
             time.sleep(5)
