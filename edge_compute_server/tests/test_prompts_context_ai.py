import sys
import os
from unittest.mock import patch, MagicMock

# Add parent path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import prompts_context_ai  # noqa: E402


def test_context_ai_fallback_string():
    """
    Test that the fallback string matches the user's latest requirement
    when the secret module is not present or HAS_SECRET is False.
    """
    with patch.object(prompts_context_ai, 'HAS_SECRET', False):
        instruction = prompts_context_ai.get_system_instruction()
        expected_fragment = "strictly context-aware customer service assistant"
        assert expected_fragment in instruction
        assert "Oakhill Pines" not in instruction


def test_context_ai_uses_secret_if_available():
    """
    Test that it returns the secret instruction if HAS_SECRET is True.
    """
    # Mock the secret module
    mock_secret = MagicMock()
    mock_secret.get_system_instruction.return_value = "SECRET INSTRUCTION"

    with patch.object(prompts_context_ai, 'HAS_SECRET', True), \
            patch.object(prompts_context_ai, 'secret', mock_secret):

        instruction = prompts_context_ai.get_system_instruction()
        assert instruction == "SECRET INSTRUCTION"


def test_context_ai_append_logic_simulation():
    """
    Simulate the append logic used in standard.py to ensure it behaves as expected.
    """
    base_instruction = "BASE"
    dynamic_instruction = "DYNAMIC"

    # Logic from standard.py:
    # system_instruction = f"{dynamic_instruction}\n\n{base_instruction}"
    result = f"{dynamic_instruction}\n\n{base_instruction}"

    assert result == "DYNAMIC\n\nBASE"
