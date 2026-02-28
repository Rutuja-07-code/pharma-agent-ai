import json
import re
import ast


def _is_as_needed(text: str) -> bool:
    t = str(text or "").lower()
    patterns = [
        r"\bas needed\b",
        r"\bif needed\b",
        r"\bwhen needed\b",
        r"\bprn\b",
        r"\bsos\b",
    ]
    return any(re.search(p, t) for p in patterns)


def _default_result(dosage_text: str):
    return _rule_based_result(dosage_text)


def _rule_based_result(dosage_text: str):
    text = str(dosage_text or "").lower()

    if _is_as_needed(text):
        return {"daily_dose": 0, "schedule_type": "as_needed"}

    units_per_administration = 1.0
    unit_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:tab(?:let)?s?|cap(?:sule)?s?|pill(?:s)?|ml|drop(?:s)?)\b",
        text,
    )
    if unit_match:
        units_per_administration = float(unit_match.group(1))

    frequency_per_day = 1
    frequency_patterns = [
        (r"\b(twice daily|2x daily|bid|bd)\b", 2),
        (r"\b(thrice daily|three times daily|3x daily|tid|tds)\b", 3),
        (r"\b(four times daily|4x daily|qid)\b", 4),
        (r"\bevery\s*12\s*hours?\b", 2),
        (r"\bevery\s*8\s*hours?\b", 3),
        (r"\bevery\s*6\s*hours?\b", 4),
        (r"\b(once daily|od)\b", 1),
        (r"\bdaily\b", 1),
    ]
    for pattern, value in frequency_patterns:
        if re.search(pattern, text):
            frequency_per_day = value
            break

    daily = units_per_administration * frequency_per_day
    daily = int(daily) if float(daily).is_integer() else daily
    return {"daily_dose": daily, "schedule_type": "regular"}


def extract_json(text):
    match = re.search(r"\{.*\}", str(text or ""), re.DOTALL)
    if not match:
        return None

    candidate = match.group().strip()

    # 1) Strict JSON
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 2) Python-style dicts (single quotes, etc.)
    try:
        parsed = ast.literal_eval(candidate)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # 3) Last-resort key extraction from loose text
    daily_match = re.search(r"daily_dose\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", candidate, re.IGNORECASE)
    schedule_match = re.search(
        r"schedule_type\s*[:=]\s*[\"']?(regular|as_needed)[\"']?",
        candidate,
        re.IGNORECASE,
    )
    if daily_match or schedule_match:
        return {
            "daily_dose": float(daily_match.group(1)) if daily_match else 1,
            "schedule_type": (schedule_match.group(1).lower() if schedule_match else "regular"),
        }

    return None


def _coerce_result(parsed, dosage_text: str):
    if not isinstance(parsed, dict):
        return None

    daily = parsed.get("daily_dose", 1)
    schedule = str(parsed.get("schedule_type", "regular")).strip().lower()

    try:
        daily = float(daily)
        daily = int(daily) if daily.is_integer() else daily
    except Exception:
        daily = 1

    if schedule not in {"regular", "as_needed"}:
        schedule = "as_needed" if _is_as_needed(dosage_text) else "regular"

    # Input intent wins for PRN/as-needed instructions.
    if _is_as_needed(dosage_text):
        schedule = "as_needed"
        daily = 0

    if schedule == "regular" and daily <= 0:
        daily = 1

    return {"daily_dose": daily, "schedule_type": schedule}


def normalize_dosage(dosage_text: str):
    deterministic = _rule_based_result(dosage_text)

    try:
        import ollama
    except ImportError:
        return deterministic

    prompt = f"""
You are a medical dosage parser.

Convert this instruction into strict JSON.

Instruction: "{dosage_text}"

Return ONLY valid JSON:
{{
  "daily_dose": number,
  "schedule_type": "regular" or "as_needed"
}}

Examples:
Input: "1 tab BD"
Output: {{"daily_dose": 2, "schedule_type": "regular"}}

Input: "Take as needed for pain"
Output: {{"daily_dose": 0, "schedule_type": "as_needed"}}
"""

    try:
        response = ollama.chat(
            model="phi",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception:
        return deterministic

    raw_output = response["message"]["content"]

    parsed = _coerce_result(extract_json(raw_output), dosage_text)

    if parsed:
        # If model misses obvious frequency cues, prefer deterministic parse.
        if (
            parsed.get("schedule_type") == "regular"
            and deterministic.get("schedule_type") == "regular"
            and deterministic.get("daily_dose") > 1
            and parsed.get("daily_dose") == 1
        ):
            return deterministic
        return parsed

    # fallback safety
    return deterministic
