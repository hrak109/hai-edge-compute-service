import os
import importlib
from unittest.mock import patch

def test_config_defaults():
    # Clear env
    with patch.dict(os.environ, {}, clear=True):
        import core.config
        importlib.reload(core.config)
        assert core.config.KAFKA_SERVER == "localhost:9092"
        assert core.config.ENABLE_RAG == False

def test_config_override():
    with patch.dict(os.environ, {"KAFKA_SERVER": "kafka:9092", "ENABLE_RAG": "True"}):
        import core.config
        importlib.reload(core.config)
        assert core.config.KAFKA_SERVER == "kafka:9092"
        assert core.config.ENABLE_RAG == True
