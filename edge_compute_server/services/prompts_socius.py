
# Try to import secret logic
try:
    from . import prompts_socius_secret as secret
    HAS_SECRET = True
except ImportError:
    HAS_SECRET = False
    secret = None


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
    bot_name = socius_context.get("bot_name") or socius_context.get("display_name", "Socius")

    return (
        f"You are {bot_name}, a helpful assistant serving as a {role} friend "
        f"to {user_name}. Answer politely and concisely."
    )


def format_user_input(user_context: dict, socius_context: dict, user_input: str) -> str:
    """
    Formats the user input if specific roles require structred prompts (e.g. Multilingual).
    """
    if HAS_SECRET and hasattr(secret, 'format_user_input'):
        return secret.format_user_input(user_context, socius_context, user_input)

    # Fallback for roles that tests expect
    from core.enums import Role
    role = socius_context.get("role")

    if role == Role.MULTILINGUAL:
        return (
            f"Instruction: Correct the user's input to Japanese and "
            f"respond/converse with the user\nInput: {user_input}"
        )
    elif role == Role.CAL_TRACKER:
        return f"calorie tracking assistant\n***RULES:\n{user_input}"
    elif role == Role.SECRETS:
        return (
            f"password and secrets keeper\n"
            f"MUST output a JSON block\n{user_input}"
        )

    return user_input
