import os

# Try to import secret logic
try:
    from . import prompts_context_ai_secret as secret
    HAS_SECRET = True
except ImportError:
    HAS_SECRET = False

def get_system_instruction() -> str:
    """
    Returns the system instruction for Context AI.
    Uses secret logic if available, otherwise returns a basic default.
    """
    if HAS_SECRET:
        return secret.get_system_instruction()
    
    # Default / Fallback Logic (Safe to commit)
    return "You are a helpful customer service assistant. Please answer the user's questions based on general knowledge."
