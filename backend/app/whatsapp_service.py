import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

WHATSAPP_FROM_DEFAULT = "whatsapp:+14155238886"
DISPATCH_LOG_FILE = Path(__file__).resolve().parents[1] / "data" / "whatsapp_dispatch_log.json"

try:
    from backend.app.order_history_store import latest_orders_by_patient_medicine
    from backend.app.refill_predictor import calculate_refill_date
except ModuleNotFoundError:
    from order_history_store import latest_orders_by_patient_medicine
    from refill_predictor import calculate_refill_date


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
def send_whatsapp_message(phone: str, message: str) -> Dict[str, Optional[str]]:
    client, error = _get_twilio_client()
    if error:
        print(f"[FAILED] to={phone} error={error}")
        return {
            "ok": False,
            "to": str(phone).strip(),
            "sid": None,
            "status": None,
            "error": error,
        }

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
        return {
            "ok": True,
            "to": to_number,
            "sid": str(getattr(msg, "sid", "") or ""),
            "status": str(getattr(msg, "status", "") or ""),
            "error": None,
        }
    except Exception as exc:
        print(f"[FAILED] to={to_number} error={exc}")
        return {
            "ok": False,
            "to": to_number,
            "sid": None,
            "status": None,
            "error": str(exc),
        }


def send_whatsapp(phone, message):
    result = send_whatsapp_message(phone, message)
    return bool(result.get("ok"))

# 🔍 Get patients whose refill is within next 2 days
def get_patients_near_refill() -> List[Dict]:
    patients_to_notify: List[Dict] = []
    latest_orders = latest_orders_by_patient_medicine()
    now = datetime.now(timezone.utc)

    for row in latest_orders:
        patient_id = str(row.get("patient_id", "")).strip()
        phone = str(row.get("phone", "")).strip()
        medicine_name = str(row.get("medicine_name", "")).strip()
        dosage_frequency = str(row.get("dosage_frequency", "")).strip() or "once daily"
        quantity = int(row.get("quantity") or 0)
        ordered_at_raw = str(row.get("ordered_at", "")).strip()

        if not patient_id or not phone or not medicine_name or quantity <= 0 or not ordered_at_raw:
            continue

        try:
            purchase_date = datetime.fromisoformat(ordered_at_raw.replace("Z", "+00:00"))
        except ValueError:
            continue

        refill_dt = calculate_refill_date(
            purchase_date=purchase_date,
            quantity=quantity,
            dosage_text=dosage_frequency,
        )

        # Skip PRN/as-needed and invalid schedules.
        if refill_dt is None:
            continue

        days_left = (refill_dt - now).days
        print(
            f"patient={patient_id} medicine={medicine_name} "
            f"phone={phone} refill_date={refill_dt.date()} days_left={days_left}"
        )

        # Notify if refill is due in next 2 days (or overdue by up to 5 days).
        if -5 <= days_left <= 2:
            patients_to_notify.append(
                {
                    "patient_id": patient_id,
                    "phone": phone,
                    "medicine_name": medicine_name,
                    "refill_date": refill_dt.date().isoformat(),
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
        dedupe_key = (
            f"{row.get('patient_id')}|{row.get('phone')}|"
            f"{row.get('medicine_name')}|{row.get('refill_date')}"
        )
        if dedupe_key in sent_keys:
            skipped += 1
            continue

        ok = send_whatsapp(
            row.get("phone", ""),
            (
                f"Hi. Your refill for {row.get('medicine_name', 'your medicine')} is due soon. "
            ),
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
