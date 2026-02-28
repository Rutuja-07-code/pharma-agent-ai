from datetime import timedelta
try:
    from backend.app.dosage_normalizer import normalize_dosage
except ModuleNotFoundError:
    from dosage_normalizer import normalize_dosage

def calculate_refill_date(purchase_date, quantity, dosage_text):

    parsed = normalize_dosage(dosage_text)

    if parsed["schedule_type"] == "as_needed":
        return None

    daily_dose = max(parsed["daily_dose"], 1)
    days_supply = quantity / daily_dose

    return purchase_date + timedelta(days=int(days_supply))
