import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

WHATSAPP_FROM_DEFAULT = "whatsapp:+14155238886"
DISPATCH_LOG_FILE = Path(__file__).resolve().parents[1] / "data" / "whatsapp_dispatch_log.json"


def _get_twilio_client():
    try:
        from twilio.rest import Client
    except Exception:
        return None, "twilio package is not installed. Run: pip install twilio"

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        return None, "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in environment variables."
    return Client(account_sid, auth_token), None


def _load_dispatch_log() -> set:
    if not DISPATCH_LOG_FILE.exists():
        return set()
    try:
        with DISPATCH_LOG_FILE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return set(payload.get("sent_keys", []))
    except Exception:
        return set()


def _save_dispatch_log(sent_keys: set) -> None:
    DISPATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DISPATCH_LOG_FILE.open("w", encoding="utf-8") as handle:
        json.dump({"sent_keys": sorted(sent_keys)}, handle, indent=2)

# 📲 Send WhatsApp message
def send_whatsapp(phone, message):
    client, error = _get_twilio_client()
    if error:
        print(f"[FAILED] to={phone} error={error}")
        return False

    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", WHATSAPP_FROM_DEFAULT)
    to_number = str(phone).strip()
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    try:
        msg = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=to_number,
        )
        print(f"[SENT] to={to_number} sid={msg.sid} status={msg.status}")
        return True
    except Exception as exc:
        print(f"[FAILED] to={to_number} error={exc}")
        return False

# 🔍 Get patients whose refill is within next 2 days
def get_patients_near_refill() -> List[Dict]:
    patients_to_notify: List[Dict] = []
    contacts_file = Path(__file__).resolve().parents[1] / "data" / "patient_contacts.csv"

    with contacts_file.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required_cols = {"phone", "last_purchase_date", "days_supply"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"patient_contacts.csv must contain columns: {sorted(required_cols)}. "
                f"Found: {reader.fieldnames or []}"
            )

        for row in reader:
            last_purchase = datetime.strptime(row["last_purchase_date"], "%Y-%m-%d")
            days_supply = int(row["days_supply"])

            refill_date = last_purchase + timedelta(days=days_supply)
            days_left = (refill_date - datetime.now()).days

            print(
                f"patient={row.get('patient_id','NA')} "
                f"phone={row.get('phone','')} refill_date={refill_date.date()} days_left={days_left}"
            )

            # Notify if refill is due in the next 2 days (or overdue by up to 5 days for testing).
            if -5 <= days_left <= 2:
                patients_to_notify.append(
                    {
                        "patient_id": row.get("patient_id", "").strip(),
                        "phone": row["phone"],
                        "refill_date": refill_date.date().isoformat(),
                    }
                )
    return patients_to_notify


def run_daily_whatsapp_reminders() -> Dict:
    rows = get_patients_near_refill()
    sent_keys = _load_dispatch_log()
    sent = 0
    failed = 0
    skipped = 0

    for row in rows:
        dedupe_key = f"{row.get('patient_id')}|{row.get('phone')}|{row.get('refill_date')}"
        if dedupe_key in sent_keys:
            skipped += 1
            continue

        ok = send_whatsapp(
            row.get("phone", ""),
            "Hi. Your medicine refill is due soon. Reply YES to reorder.",
        )
        if ok:
            sent += 1
            sent_keys.add(dedupe_key)
        else:
            failed += 1

    _save_dispatch_log(sent_keys)
    summary = {
        "eligible": len(rows),
        "sent": sent,
        "failed": failed,
        "skipped_already_sent": skipped,
    }
    print(f"[WHATSAPP_REMINDER_SUMMARY] {summary}")
    return summary


if __name__ == "__main__":
    run_daily_whatsapp_reminders()
