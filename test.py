# test_refill.py

# test_full_pipeline.py

# from backend.app.refill_engine import get_refill_dataframe

# df = get_refill_dataframe("backend/data/Consumer Order History 1.xlsx")

# print(df[["product_name", "next_refill_date"]].head())

from pathlib import Path

from backend.app.refill_engine import get_due_refills

DATA_FILE = Path(__file__).resolve().parent / "backend" / "data" / "Consumer Order History 1.xlsx"
due = get_due_refills(str(DATA_FILE))

print(due[["patient_id", "product_name", "next_refill_date"]])
