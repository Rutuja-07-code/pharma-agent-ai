# #LLM based orderJSON
# # used ollama model phi 
# #worked
# #still wants work on it for chat version 

# import requests
# import json
# import re


# def extract_order(user_message):

#     prompt = f"""
# Extract medicine_name, quantity, unit.
# Return ONLY JSON object.

# User message: "{user_message}"
# """

#     response = requests.post(
#         "http://localhost:11434/api/generate",
#         json={
#             "model": "phi",
#             "prompt": prompt,
#             "stream": False
#         }
#     )

#     output = response.json()["response"]

#     # ✅ Extract JSON part only
#     match = re.search(r"\{.*?\}", output, re.DOTALL)

#     if match:
#         json_text = match.group()
#         try:
#             parsed = json.loads(json_text)
#             if not isinstance(parsed, dict):
#                 return {"error": "Invalid JSON shape", "raw_output": output}

#             medicine_name = str(parsed.get("medicine_name", "")).strip()

#             try:
#                 quantity = int(parsed.get("quantity", 1))
#             except (TypeError, ValueError):
#                 quantity = 1

#             unit_raw = str(parsed.get("unit", "strip")).strip().lower()
#             unit_map = {
#                 "strip": "strip",
#                 "strips": "strip",
#                 "stirp": "strip",
#                 "stirps": "strip",
#                 "tablet": "tablet",
#                 "tablets": "tablet",
#                 "bottle": "bottle",
#                 "bottles": "bottle",
#             }
#             unit = unit_map.get(unit_raw, "strip")

#             return {
#                 "medicine_name": medicine_name,
#                 "quantity": quantity,
#                 "unit": unit,
#             }
#         except json.JSONDecodeError:
#             return {
#                 "error": "Invalid JSON returned by model",
#                 "raw_output": output,
#                 "json_text": json_text,
#             }

#     return {
#         "error": "No JSON found",
#         "raw_output": output
#     }
# print(extract_order("I need paracetamol 28 strips "))






# import requests
# import json
# import re

# def extract_order(user_message):

#     response = requests.post(
#         "http://localhost:11434/api/chat",
#         json={
#             "model": "phi",
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": "Return ONLY a JSON object with medicine_name, quantity, unit, priscription"
#                 },
#                 {
#                     "role": "user",
#                     "content": f"""
# Extract:
# - medicine_name
# - quantity
# - unit

# Message: "{user_message}"
# """
#                 }
#             ],
#             "stream": False
#         }
#     )

#     output = response.json()["message"]["content"]

#     print("\nRAW OUTPUT FROM OLLAMA:\n", output)

#     # ✅ Extract JSON object only
#     match = re.search(r"\{.*?\}", output, re.DOTALL)

#     if match:
#         json_text = match.group()
#         return json.loads(json_text)

#     return {"error": "No valid JSON found", "raw_output": output}


# # Test
# print(extract_order("I want Cetirizine 28 strips only"))





import requests
import json

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
            "stream": False
        }
    )

    result = response.json()

    return json.loads(result["message"]["content"])
print(extract_order("I want Cetirizine 28 strips only"))
