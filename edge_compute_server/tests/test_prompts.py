import sys
import os
import pytest  # noqa: F401

# Add parent path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompts_socius import get_system_instruction, format_user_input  # noqa: E402
from core.enums import Role, Language  # noqa: E402


def test_system_instruction_basic():
    user = {"display_name": "User"}
    socius = {"role": "casual", "display_name": "Socius", "tone": "friendly"}

    instr = get_system_instruction(user, socius)
    assert "You are Socius" in instr
    assert "casual friend" in instr


def test_system_instruction_multilingual_japanese():
    user = {"language": Language.ENGLISH}
    socius = {
        "role": Role.MULTILINGUAL,
        "multilingual_selection": Language.JAPANESE,
        "bot_gender": "female",
        "bot_name": "Mika"
    }

    # Logic moved to format_user_input
    user_input = "Hello"
    result = format_user_input(user, socius, user_input)

    assert "Instruction: Correct the user's input to Japanese" in result
    assert "respond/converse with the user" in result


def test_system_instruction_calorie_tracker():
    user = {}
    socius = {"role": Role.CAL_TRACKER}

    # Logic moved to format_user_input
    user_input = "I ate pizza"
    result = format_user_input(user, socius, user_input)

    assert "calorie tracking assistant" in result
    assert "***RULES:" in result


def test_system_instruction_secrets():
    user = {}
    socius = {"role": Role.SECRETS}

    # Logic moved to format_user_input
    user_input = "my secret"
    result = format_user_input(user, socius, user_input)

    assert "password and secrets keeper" in result
    assert "MUST output a JSON block" in result
