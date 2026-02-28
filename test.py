# test_refill.py

# test_full_pipeline.py

# from backend.app.refill_engine import get_refill_dataframe

# df = get_refill_dataframe("backend/data/Consumer Order History 1.xlsx")

# print(df[["product_name", "next_refill_date"]].head())

# from pathlib import Path

# from backend.app.refill_engine import get_due_refills

# DATA_FILE = Path(__file__).resolve().parent / "backend" / "data" / "Consumer Order History 1.xlsx"
# due = get_due_refills(str(DATA_FILE))

# print(due[["patient_id", "product_name", "next_refill_date"]])
# from backend.app.whatsapp_service import send_whatsapp

# response = send_whatsapp(
#     "+917498540670",
#     "Hello Rutz 🚀 Pharma AI test message"
# )

# print(response)
from twilio.rest import Client
import os

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
m = client.messages("SM1efc02be389edc0f1a7b1e3a9be9f49c").fetch()
print(m.status, m.error_code, m.error_message)
