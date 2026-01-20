import json
import urllib.request
import urllib.error
import os

# --- Configuration ---
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "soc-model" # Assuming this is the model name

# --- Copied Logic from llm_worker.py (with latest updates) ---

def get_system_instruction(user_context: dict, socius_context: dict) -> str:
    # 1. Determine Role and Attributes
    role = socius_context.get("role") or "casual"
    bot_name = socius_context.get("display_name") or "Socius"
    tone = socius_context.get("tone") or "friendly"
    intimacy = socius_context.get("intimacy_level") or 5
    
    # Base Instruction
    instruction = f"You are {bot_name}, a {role}."
    
    if role == 'multilingual':
        # 1. Configuration
        LANG_CODE_MAP = {
            'en': 'English', 'ko': 'Korean', 'ja': 'Japanese',
            'zh': 'Chinese', 'es': 'Spanish', 'fr': 'French', 'de': 'German'
        }

        selection = socius_context.get('multilingual_selection')
        target_lang = LANG_CODE_MAP.get(selection, 'English')
        
        user_lang_code = user_context.get("language")
        user_lang = LANG_CODE_MAP.get(user_lang_code, 'English')
        
        bot_name = socius_context.get('bot_name', 'Socius')
        bot_gender = socius_context.get('bot_gender', 'female')
        
        # 2. Pronoun & Persona Logic
        if bot_gender == 'female':
            pronoun_rule = "Use 'Watashi(私)'. FORBIDDEN: 'Boku', 'Ore'."
        else:
            pronoun_rule = "Use 'Boku(僕)' or 'Ore(俺)'."

        # 3. Dynamic Rules
        formatting_instructions = ""
        pronunciation_instruction = "Standard Romanization"
        
        if target_lang == 'Japanese':
            formatting_instructions = """
            - **JAPANESE SYNTAX:** You must use `Kanji(Hiragana)` syntax for ALL Kanji.
            - *Correct:* `私(わたし)`
            - *Incorrect:* `私`
            """
            if user_lang == 'Korean':
                pronunciation_instruction = """
                **Korean Hangul Transcription**
                - **CRITICAL:** Write the *sounds* of Block 1 using ONLY Korean Hangul characters.
                - **NO JAPANESE CHARACTERS:** Do NOT use Hiragana, Katakana, or Kanji in Block 2. Only 한글.
                - **PHONETIC ONLY:** Transcribe the SOUND, not the meaning.
                  - `本当(ほんとう)` -> `혼토` (NOT `진짜`)
                  - `ありがとう` -> `아리가토` (NOT `고마워`)
                  - `一緒に(いっしょに)` -> `잇쇼니` (NOT `함께`)
                  - `行きましょう(いきましょう)` -> `이키마쇼` (NOT `가요`)
                """
            else:
                pronunciation_instruction = "**Standard Romaji**"

        # 4. The "Ownership-Anchored" Compiler Prompt
        instruction += f"""
        ### SYSTEM ROLE: RAW TEXT COMPILER
        **YOU ARE NOT A CHATBOT.** You are a backend processor.
        Your task is to convert input into strict text blocks separated by blank lines.

        ### INPUT DATA
        - **Target Language:** {target_lang}
        - **User Language:** {user_lang}
        - **Bot Identity:** {bot_name} ({bot_gender})

        ### COMPILATION CONSTRAINTS (INSTANT FAIL)
        1. **NO LABELS:** Do not write "Corrected:", "Block 1:", etc. Just output the content.
        2. **SPEAKER INTEGRITY:**
        - **Block 1** is the **USER** speaking (Corrected). DO NOT change the User's pronouns (`俺`, `僕`, `私`). Keep the User's voice.
        - **Block 4** is the **BOT** speaking (Reply).
        3. **PRONOUN LOCK (Block 4 ONLY):** {pronoun_rule} This rule applies ONLY to Block 4, the Bot's reply.
        4. **STRICT SPACING:** Double newline between every block.

        {formatting_instructions}

        ### SCENARIO A: IF USER MAKES A MISTAKE OR NEEDS POLISHING
        Output exactly **5 blocks** in this order:

        [BLOCK 1: The USER'S sentence, grammatically corrected in {target_lang}]
        *(Constraint: KEEP the User's original meaning AND pronouns. If User says '俺の家', Block 1 MUST say '俺の家'.)*
        
        [BLOCK 2: The Sound of BLOCK 1 using {pronunciation_instruction}]
        *(Constraint: PHONETIC TRANSCRIPTION ONLY. Write how Block 1 SOUNDS, not what it MEANS.)*
        *(Example: `昨日(きのう)` → `키노` (SOUND). NOT `어제` (MEANING).)*
        
        [BLOCK 3: Explanation of the correction in {user_lang}]
        *(Constraint: EVERY WORD in Block 3 MUST be {user_lang}. FORBIDDEN: Any {target_lang} text in this block.)*
        
        [BLOCK 4: Reply from {bot_name} in {target_lang}]
        *(Constraint: {bot_name} replies to Block 1. Use friendly tone.)*
        
        [BLOCK 5: Translation of BLOCK 4 in {user_lang}]
        *(Constraint: Translate the MEANING of Block 4 into {user_lang}. This is different from Block 2.)*

        ### SCENARIO B: IF USER INPUT IS PERFECT
        Output exactly **2 blocks**:

        [BLOCK 1: Reply from {bot_name} in {target_lang}]
        
        [BLOCK 2: Translation of BLOCK 1 in {user_lang}]

        ### EXECUTION TASK
        Analyze the user input below. Choose Scenario A or B. Output the raw text blocks ONLY.
        """
    return instruction

def query_ollama(model: str, messages: list[dict]) -> str:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {}).get('content', "Error: No content in response")
    except urllib.error.URLError as e:
        return f"Error connecting to AI model: {e}"

# --- Test Case ---

def run_test():
    # Contexts matching the user's scenario
    user_context = {
        "language": "ko",
        "display_name": "User"
    }
    socius_context = {
        "role": "multilingual",
        "multilingual_selection": "ja", # Target Japanese
        "bot_name": "Socius",
        "bot_gender": "female"
    }
    
    # Input text that likely triggered the issue
    # Attempting to say: "Can I go to your house with you?"
    # Mistake similar to user's log: "私(わたし)は、あなたと一緒(いっしょ)に、私(わたし)の家(いえ)に行(い)きませんか？"
    # Wait, the user's log showed the *corrected* version first. 
    # Let's try a raw input example: "Isshoni anata no ie ni iku?" (Let's go to your house?)
    input_text = "昨日友達と映画を見に行ったけど、思ったより面白くなかったから、途中で帰っちゃった。" 
    
    print("\n-------------------------------------------------")
    print(f"TEST INPUT: {input_text}")
    print("-------------------------------------------------")

    system_instruction = get_system_instruction(user_context, socius_context)
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": input_text}
    ]
    
    response = query_ollama(MODEL, messages)
    
    print("\n--- LLM RESPONSE ---")
    print(response)
    print("\n-------------------------------------------------")

if __name__ == "__main__":
    run_test()
