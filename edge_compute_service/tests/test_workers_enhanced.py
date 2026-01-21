import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.standard import run_worker
# Partial import for RAG worker - we'll mock the internal dependencies
import workers.rag_worker

class TestStandardWorker(unittest.TestCase):
    @patch('workers.standard.create_consumer')
    @patch('workers.standard.create_producer')
    @patch('workers.standard.query_ollama')
    def test_run_worker_success(self, mock_query, mock_producer, mock_consumer):
        # Setup Mocks
        mock_msg = MagicMock()
        mock_msg.value = {
            "question_id": "q123",
            "text": "Hello",
            "timestamp": datetime.utcnow().isoformat(),
            "model": "gemma:2b"
        }
        # Simulate one message then stop loop (by raising exception or just returning empty)
        # However, the loop iterates over consumer. Ideally we pass a list.
        # Since create_consumer returns the consumer object, we make it iter over a list
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.__iter__.return_value = [mock_msg]
        mock_consumer.return_value = mock_consumer_instance
        
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance
        
        mock_query.return_value = "Hello back!"

        # Run
        with patch('workers.standard.print'): # Suppress print
            run_worker()

        # Verify
        mock_query.assert_called()
        mock_producer_instance.send.assert_called_with(
            'answers',
            value={
                "question_id": "q123",
                "answer": "Hello back!",
                "user_id": None,
                "service": None,
                "model": "gemma:2b",
                "context": None
            }
        )
        mock_producer_instance.flush.assert_called()

    @patch('workers.standard.create_consumer')
    @patch('workers.standard.create_producer')
    def test_run_worker_stale_message(self, mock_producer, mock_consumer):
        # Setup Stale Message
        old_time = (datetime.utcnow() - timedelta(minutes=40)).isoformat()
        mock_msg = MagicMock()
        mock_msg.value = {
            "question_id": "qStale",
            "text": "Old news",
            "timestamp": old_time
        }
        
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.__iter__.return_value = [mock_msg]
        mock_consumer.return_value = mock_consumer_instance

        # Run
        with patch('workers.standard.print'):
             with patch('workers.standard.logging') as mock_log:
                run_worker()
                # Verify warning logged
                mock_log.warning.assert_called()

        # Verify NO producer call
        mock_producer.return_value.send.assert_not_called()


class TestRagWorker(unittest.TestCase):
    @patch('workers.rag_worker.create_consumer')
    @patch('workers.rag_worker.create_producer')
    @patch('workers.rag_worker.ChatMessage')
    @patch('workers.rag_worker.Ollama') # Mock the Ollama class itself
    def test_run_rag_worker(self, mock_ollama_cls, mock_chat_message, mock_producer, mock_consumer):
        # Setup
        mock_msg = MagicMock()
        mock_msg.value = {
            "question_id": "qRag",
            "text": "RAG Question",
            "model": "llama3"
        }
        
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.__iter__.return_value = [mock_msg]
        mock_consumer.return_value = mock_consumer_instance
        
        # Mock LLM instance
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.message.content = "RAG Answer"
        mock_llm_instance.chat.return_value = mock_response
        mock_ollama_cls.return_value = mock_llm_instance

        # Run
        # We need to ensure workers.rag_worker.Ollama is not None
        # The test patch should handle this if it imported successfully.
        
        # Enable print for debugging
        # with patch('workers.rag_worker.print'):
        workers.rag_worker.run_rag_worker()

        # Verify
        mock_ollama_cls.assert_called() # Should initialize LLM
        mock_llm_instance.chat.assert_called()
        mock_producer.return_value.send.assert_called_with(
            'answers',
            value={
                "question_id": "qRag",
                "answer": "RAG Answer",
                "user_id": None,
                "service": None,
                "model": "llama3"
            }
        )

if __name__ == '__main__':
    unittest.main()
