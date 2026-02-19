import json
import urllib.request
import urllib.error
from core.config import OLLAMA_BASE_URL


def query_ollama(model: str, messages: list[dict], num_predict: int = 200) -> str:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 512,
            "num_predict": num_predict
        }
    }

    # Log Request
    system_instruction = next((m["content"] for m in messages if m["role"] == "system"), "None")
    user_question = next((m["content"] for m in messages if m["role"] == "user"), "None")
    print(
        f"\n[LLM Request]\nModel: {model}\nSystem Instruction: {system_instruction}\nUser Question: {user_question}\n",
        flush=True
    )

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode('utf-8'))

            # Log Stat
            eval_count = result.get('eval_count', 0)
            eval_duration = result.get('eval_duration', 0)
            if eval_count > 0 and eval_duration > 0:
                tps = eval_count / (eval_duration / 1e9)
                print(
                    f"STATS: Generated {eval_count} tokens in {eval_duration / 1e9:.2f}s ({tps:.2f} tokens/sec)",
                    flush=True
                )

            return result.get('message', {}).get('content', "Error: No content in response")
    except urllib.error.URLError as e:
        print(f"Error calling Ollama: {e}", flush=True)
        return f"Error connecting to AI model: {e}"


def get_model_details(model: str) -> str:
    url = f"{OLLAMA_BASE_URL}/api/show"
    payload = {"name": model}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            details = result.get('details', {})
            parent_model = details.get('parent_model', '')
            family = details.get('family', '')
            quant_level = details.get('quantization_level', 'Unknown')

            info_str = f"Family: {family}, Quant: {quant_level}"
            if parent_model:
                info_str += f", Parent: {parent_model}"

            modelfile = result.get('modelfile', '')
            for line in modelfile.split('\n'):
                if line.upper().startswith('FROM'):
                    info_str += f", Base: {line.split(' ', 1)[1]}"
                    break

            return info_str
    except Exception as e:
        return f"Could not fetch details: {e}"
