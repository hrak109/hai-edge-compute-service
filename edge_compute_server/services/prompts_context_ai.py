
# Try to import secret logic
try:
    from . import prompts_context_ai_secret as secret
    HAS_SECRET = True
except ImportError:
    HAS_SECRET = False
    secret = None


def get_system_instruction() -> str:
    """
    Returns the system instruction for Context AI.
    Uses secret logic if available, otherwise returns a basic default.
    """
    if HAS_SECRET:
        return secret.get_system_instruction()

    # Default / Fallback Logic (Safe to commit)
    return (
        "You are a strictly context-aware customer service assistant. "
        "CRITICAL: Only answer questions using the provided context. "
        "Do not use outside knowledge. If the information is missing, "
        "you MUST say: 'I don't have that information, please contact the office!'"
    )
