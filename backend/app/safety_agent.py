from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"

def _normalize_text(value):
    return str(value or "").strip().lower()


def safety_check(order):
    med = order.get("medicine_name")
    if not med:
        return {"status": "Rejected", "reason": "Missing medicine name"}

    try:
        qty = int(order.get("quantity"))
    except (TypeError, ValueError):
        return {"status": "Rejected", "reason": "Invalid quantity"}

    # Always read fresh inventory so stock checks are up to date.
    df = pd.read_csv(DATA_FILE)
    med_norm = _normalize_text(med)
    names_norm = df["medicine_name"].astype(str).str.strip().str.lower()

    # Prefer exact normalized match to avoid false positives from broad substring matches.
    exact_match = df[names_norm == med_norm]
    if not exact_match.empty:
        match = exact_match
    else:
        # Substring fallback for slight extractor variations; keep regex disabled.
        match = df[df["medicine_name"].astype(str).str.contains(str(med), case=False, na=False, regex=False)]

    if match.empty:
        return {"status": "Rejected", "reason": "Medicine not found"}

    stock = int(match.iloc[0]["stock"])
    prescription = str(match.iloc[0]["prescription_required"]).strip()

    if stock <= 0:
        return {
            "status": "Rejected",
            "reason": f"{med} is out of stock",
            "stock": stock,
            "prescription_required": prescription,
        }

    if stock < qty:
        return {
            "status": "Partial",
            "reason": f"Only {stock} units available (requested {qty})",
            "stock": stock,
            "requested": qty,
            "prescription_required": prescription,
        }

    return {
        "status": "InStock",
        "reason": "Stock available",
        "stock": stock,
        "requested": qty,
        "prescription_required": prescription,
    }
