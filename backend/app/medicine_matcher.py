import pandas as pd
from pathlib import Path
import re

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"


def _load_inventory():
    # Read fresh CSV every time so matching uses current inventory.
    return pd.read_csv(DATA_FILE)


def _normalize_name(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def find_medicine_matches(user_med_name):
    """
    Returns:
    - None if no match
    - One medicine name if exact/single match
    - List of matches if multiple found
    """

    query = _normalize_name(user_med_name)
    if not query:
        return None

    df = _load_inventory()
    if "medicine_name" not in df.columns:
        return None

    rows = []
    seen = set()
    query_tokens = [token for token in query.split() if token]

    for medicine_name in df["medicine_name"].dropna().astype(str):
        normalized_name = _normalize_name(medicine_name)
        if not normalized_name:
            continue

        score = None
        if normalized_name == query:
            score = 0
        elif normalized_name.startswith(query):
            score = 1
        elif f" {query} " in f" {normalized_name} ":
            score = 2
        elif query in normalized_name:
            score = 3
        elif query_tokens and all(token in normalized_name for token in query_tokens):
            score = 4

        if score is None:
            continue

        dedupe_key = normalized_name
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append((score, len(normalized_name), medicine_name))

    if not rows:
        return None

    rows.sort(key=lambda item: (item[0], item[1], item[2].lower()))
    matches = [medicine_name for _, _, medicine_name in rows[:5]]

    if len(matches) == 1:
        return matches[0]

    return matches
