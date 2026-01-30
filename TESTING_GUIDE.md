# Testing Guide - Edge Compute Server

This guide covers how to run unit tests and perform manual verification for the `edge_compute_server`.

## 1. Prerequisites

Ensure you have the following installed:
- Python 3.10+
- Docker & Docker Compose
- Virtual Environment (recommended)

## 2. Unit Tests

The project uses `pytest` for unit testing. Configuration validation and prompt logic are tested here.

### Setup
Activate your virtual environment:
```bash
source venv/bin/activate
```
*If you don't have a venv:*
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests
Execute the tests using the module syntax to ensure proper import resolution:
```bash
python -m pytest
```

**Expected Output:**
```
tests/test_config.py ..
tests/test_prompts.py ....
```

## 3. Manual / Integration Testing

Since the worker listens to Kafka topics, manual testing involves sending messages to these topics and observing the worker logs.

### Step 1: Start the Services
```bash
docker-compose up --build
```
Ensure `llm_worker_main` starts successfully and logs:
> Standard Worker starting for topics: ['questions-socius', 'questions-context-ai', 'questions-rag']

### Step 2: Send Test Messages

You can use the built-in Kafka console producer inside the container or a generic Kafka tool.

**Using Docker & Kafka Console Producer:**

1.  **Exec into Kafka container:**
    ```bash
    docker exec -it kafka /bin/bash
    ```
(Note: Container name might vary, check with `docker ps`. It might be `kafka` or `hai-service-kafka-1` depending on where it's running).

2.  **Send message to "questions-socius" (Standard LLM):**
    ```bash
    kafka-console-producer --bootstrap-server localhost:9092 --topic questions-socius
    ```
    *Input JSON payload:*
    ```json
    {"question_id": "test-1", "text": "Hello, who are you?", "user_id": 123, "service": "socius"}
    ```

3.  **Send message to "questions-rag" (RAG Engine):**
    ```bash
    kafka-console-producer --bootstrap-server localhost:9092 --topic questions-rag
    ```
    *Input JSON payload:*
    ```json
    {"question_id": "rag-1", "text": "What is in my knowledge base?", "user_id": 123, "service": "socius"}
    ```

### Step 3: Verify Logs
Check the `llm_worker_main` logs:
```bash
docker logs -f <container_id_of_llm_worker>
```

**Standard Success:**
> DEBUG: Processing question ID: test-1 ... Topic: questions-socius
> Answered: test-1

**RAG Success:**
> DEBUG: Processing question ID: rag-1 ... Topic: questions-rag
> RAG Query: What is in my knowledge base? ...
> Answered: rag-1

## 4. Configuration Testing

Changes to `.env` or `config.py` can be verified by running `tests/test_config.py`.
Remember that strictly defined variables (no defaults) in `config.py` MUST be present in your environment (or `.env` file loaded by Docker).
