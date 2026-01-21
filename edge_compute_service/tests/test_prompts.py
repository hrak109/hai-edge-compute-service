import pytest
import sys
import os

# Add parent path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompts import get_system_instruction

def test_system_instruction_basic():
    user = {"display_name": "User"}
    socius = {"role": "casual", "display_name": "Socius", "tone": "friendly"}
    
    instr = get_system_instruction(user, socius)
    assert "You are Socius" in instr
    assert "casual friend" in instr

def test_system_instruction_multilingual_japanese():
    user = {"language": "en"}
    socius = {
        "role": "multilingual", 
        "multilingual_selection": "ja", 
        "bot_gender": "female",
        "bot_name": "Mika"
    }
    
    instr = get_system_instruction(user, socius)
    assert "**Target Language:** Japanese" in instr
    assert "raw text blocks ONLY" in instr
    assert "Use 'Watashi(私)'" in instr
    # Check block structure constraint
    assert "[BLOCK 1:" in instr

def test_system_instruction_calorie_tracker():
    user = {}
    socius = {"role": "cal_tracker"}
    
    instr = get_system_instruction(user, socius)
    assert "You are a Calorie Tracker Helper" in instr
    assert "output a JSON block" in instr

def test_system_instruction_secrets():
    user = {}
    socius = {"role": "secrets"}
    instr = get_system_instruction(user, socius)
    assert "password and secrets keeper" in instr
    assert "password_event" in instr
