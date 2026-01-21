import os
from kafka import KafkaConsumer

KAFKA_SERVER = os.getenv("KAFKA_SERVER", "kafka-tunnel:9092")
# Default to questions-socius if not set, but inside container it should be set
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "questions-socius") 
GROUP_ID = f"worker-group-{TOPIC_NAME}"

print(f"Connecting to {KAFKA_SERVER} for topic {TOPIC_NAME}, group {GROUP_ID}...", flush=True)

try:
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[KAFKA_SERVER],
        group_id=GROUP_ID,
        auto_offset_reset='earliest',
        enable_auto_commit=False 
    )

    print("Consumer connected. Polling to join group...", flush=True)
    # Poll to ensure assignment
    consumer.poll(timeout_ms=2000)

    partitions = consumer.assignment()
    if not partitions:
        print("No partitions assigned. Maybe topic doesn't exist or group issues?", flush=True)
    else:
        print(f"Assigned partitions: {partitions}", flush=True)
        
        # Seek to end
        consumer.seek_to_end()
        for p in partitions:
            print(f"Partition {p.partition}: New offset {consumer.position(p)}", flush=True)
            
        consumer.commit()
        print("Offsets committed to end. Queue cleared for this worker group.", flush=True)

    consumer.close()

except Exception as e:
    print(f"Error: {e}")
