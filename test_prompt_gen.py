import sys
import os
from unittest.mock import MagicMock

# Mock kafka before importing llm_worker
sys.modules['kafka'] = MagicMock()

# Add the current directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'edge_compute_service'))

from llm_worker import get_system_instruction

def test_prompt(name, user_ctx, socius_ctx):
    print(f"\n--- TEST: {name} ---")
    prompt = get_system_instruction(user_ctx, socius_ctx)
    print(prompt)
    print("-" * 30)

# Case 1: English User learning Korean
user_ctx_1 = {"language": "en", "display_name": "John"}
socius_ctx_1 = {"role": "multilingual", "multilingual_selection": "ko", "display_name": "Socius", "tone": "friendly"}
test_prompt("English -> Korean", user_ctx_1, socius_ctx_1)

# Case 2: Korean User learning English
user_ctx_2 = {"language": "ko", "display_name": "Min-su"}
socius_ctx_2 = {"role": "multilingual", "multilingual_selection": "en", "display_name": "Socius", "tone": "friendly"}
test_prompt("Korean -> English", user_ctx_2, socius_ctx_2)

# Case 3: English User learning Japanese
user_ctx_3 = {"language": "en", "display_name": "Alice"}
socius_ctx_3 = {"role": "multilingual", "multilingual_selection": "ja", "display_name": "Socius", "tone": "friendly"}
test_prompt("English -> Japanese", user_ctx_3, socius_ctx_3)
