# Prescription validation + stock rules
#done,worked

from pathlib import Path
import pandas as pd

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
df = pd.read_csv(DATA_FILE)


# Load medicine data
def safety_check(order):
    med = order["medicine_name"]
    try:
        qty = int(order["quantity"])
    except (TypeError, ValueError):
        return {"status": "Rejected", "reason": "Invalid quantity"}

    # Find medicine
    match = df[df["medicine_name"].str.contains(med, case=False)]

    if match.empty:
        return {"status": "Rejected", "reason": "Medicine not found"}

    stock = int(match["stock"].values[0])
    prescription = match["prescription_required"].values[0]

    # Stock check
    if stock < qty:
        return {"status": "Rejected", "reason": "Out of stock"}

    # Prescription check
    if prescription == "Yes":
        return {"status": "Rejected", "reason": "Prescription required"}

    return {"status": "Approved", "reason": "Order allowed"}
