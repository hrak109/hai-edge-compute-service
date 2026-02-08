import os
import importlib
from unittest.mock import patch


def test_config_defaults():
    # Clear env
    with patch.dict(os.environ, {}, clear=True):
        import core.config
        importlib.reload(core.config)
        assert core.config.KAFKA_SERVER is None


def test_config_override():
    with patch.dict(os.environ, {"KAFKA_SERVER": "kafka:9092"}):
        import core.config
        importlib.reload(core.config)
        assert core.config.KAFKA_SERVER == "kafka:9092"
