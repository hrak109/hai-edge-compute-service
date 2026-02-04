import os

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
    role = socius_context.get("role", Role.FORMAL)
    user_name = user_context.get("display_name", "User")
    
    return f"You are a helpful assistant serving as a {role} friend to {user_name}. Answer politely and concisely."
