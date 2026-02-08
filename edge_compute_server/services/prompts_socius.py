
# Try to import secret logic
try:
    from . import prompts_socius_secret as secret
    HAS_SECRET = True
except ImportError:
    HAS_SECRET = False


def get_system_instruction(user_context: dict, socius_context: dict) -> str:
    """
    Returns the system instruction for Socius/Friends.
    Uses secret logic if available, otherwise returns a basic default.
    """
    if HAS_SECRET:
        return secret.get_system_instruction(user_context, socius_context)

    # Default / Fallback Logic (Safe to commit)
    from core.enums import Role
    role = socius_context.get("role", Role.CASUAL)
    user_name = user_context.get("display_name", "User")

    return f"You are a helpful assistant serving as a {role} friend to {user_name}. Answer politely and concisely."


def format_user_input(user_context: dict, socius_context: dict, user_input: str) -> str:
    """
    Formats the user input if specific roles require structred prompts (e.g. Multilingual).
    """
    if HAS_SECRET and hasattr(secret, 'format_user_input'):
        return secret.format_user_input(user_context, socius_context, user_input)

    return user_input
