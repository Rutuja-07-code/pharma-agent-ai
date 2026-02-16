# #LLM based orderJSON
# # used ollama model phi 
# #worked


import ast
import json
import re
import requests


def _extract_json_dict(text):
    text = (text or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Some models return Python dict text with single quotes.
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except (SyntaxError, ValueError):
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except (SyntaxError, ValueError):
            return None

    return None


def _normalize_order_keys(parsed):
    if not isinstance(parsed, dict):
        return {"error": "Invalid order format from model", "raw_output": parsed}

    medicine_name = (
        parsed.get("medicine_name")
        or parsed.get("medicine")
        or parsed.get("drug_name")
    )
    quantity = parsed.get("quantity")
    unit = parsed.get("unit", "strip")

    if not medicine_name:
        return {"error": "Missing medicine_name in model output", "raw_output": parsed}

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return {"error": "Missing or invalid quantity in model output", "raw_output": parsed}

    return {
        "medicine_name": str(medicine_name).strip(),
        "quantity": quantity,
        "unit": str(unit).strip().lower() if unit else "strip",
    }

def extract_order(user_message):

    prompt = f"""
    You are an expert pharmacist AI.

    Extract:
    - medicine_name
    - quantity
    - unit

    Return ONLY valid JSON.
    No extra explanation.

    User message:
    "{user_message}"
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "phi",
                "messages": [
                    {
                        "role": "system",
                        "content": "Return ONLY JSON. No extra text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        return {"error": f"LLM service unavailable: {exc}"}

    content = result.get("message", {}).get("content", "")
    parsed = _extract_json_dict(content)

    if parsed is None:
        return {"error": "No valid JSON returned by model", "raw_output": content}

    return _normalize_order_keys(parsed)
