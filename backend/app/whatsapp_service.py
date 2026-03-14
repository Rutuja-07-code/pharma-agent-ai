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

        days_until_refill = (refill_dt.date() - now.date()).days
        if days_until_refill < 0 or days_until_refill > 2:
            continue

        patients_to_notify.append(
            {
                "patient_id": patient_id,
                "phone": phone,
                "medicine_name": medicine_name,
                "quantity": quantity,
                "dosage_frequency": dosage_frequency,
                "ordered_at": ordered_at_raw,
                "refill_date": refill_dt.isoformat(),
                "days_until_refill": days_until_refill,
            }
        )

    return patients_to_notify


def run_daily_whatsapp_reminders() -> Dict[str, object]:
    patients = get_patients_near_refill()
    sent_keys = _load_dispatch_log()
    sent_count = 0
    skipped_count = 0
    errors: List[Dict[str, str]] = []

    for row in patients:
        patient_id = str(row.get("patient_id", "")).strip()
        phone = str(row.get("phone", "")).strip()
        medicine_name = str(row.get("medicine_name", "")).strip()
        refill_date = str(row.get("refill_date", "")).strip()
        days_until_refill = int(row.get("days_until_refill", 0) or 0)
        dispatch_key = f"{patient_id}|{medicine_name}|{refill_date}"

        if not patient_id or not phone or not medicine_name or not refill_date:
            skipped_count += 1
            continue

        if dispatch_key in sent_keys:
            skipped_count += 1
            continue

        if days_until_refill <= 0:
            timing_text = "today"
        elif days_until_refill == 1:
            timing_text = "tomorrow"
        else:
            timing_text = f"in {days_until_refill} days"

        message = (
            f"Reminder: your medicine '{medicine_name}' may need a refill {timing_text}. "
            "Reply here if you want to place an order."
        )
        result = send_whatsapp_message(phone, message)
        if result.get("ok"):
            sent_keys.add(dispatch_key)
            sent_count += 1
        else:
            errors.append(
                {
                    "patient_id": patient_id,
                    "phone": phone,
                    "medicine_name": medicine_name,
                    "error": str(result.get("error") or "Unknown error"),
                }
            )

    _save_dispatch_log(sent_keys)
    return {
        "checked": len(patients),
        "sent": sent_count,
        "skipped": skipped_count,
        "errors": errors,
    }
