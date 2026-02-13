#LLM based orderJSON extraction
# used ollama model phi 
#worked
import requests
import json
import re

def extract_order(user_message):

    prompt = f"""
Extract medicine_name, quantity, unit.
Return ONLY JSON object.

User message: "{user_message}"
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi",
            "prompt": prompt,
            "stream": False
        }
    )

    output = response.json()["response"]

    # ✅ Extract JSON part only
    match = re.search(r"\{.*\}", output, re.DOTALL)

    if match:
        json_text = match.group()
        return json.loads(json_text)

    return {
        "error": "No JSON found",
        "raw_output": output
    }


print(extract_order("I need ghf two daily , 28 strips "))
