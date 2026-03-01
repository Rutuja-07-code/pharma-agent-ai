import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ORDER_HISTORY_FILE = Path(__file__).resolve().parents[1] / "data" / "order_history.jsonl"


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_phone(value: Any) -> str:
    raw = _normalize_text(value)
    if not raw:
        return ""
    if raw.startswith("+"):
        digits = "".join(ch for ch in raw[1:] if ch.isdigit())
        return f"+{digits}" if digits else ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+91{digits}"
    return f"+{digits}"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_order_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    patient_id = _normalize_text(payload.get("patient_id"))
    username = _normalize_text(payload.get("username"))
    phone = _normalize_phone(payload.get("phone"))
    medicine_name = _normalize_text(payload.get("medicine_name"))
    dosage_frequency = _normalize_text(payload.get("dosage_frequency"))
    ordered_at = _normalize_text(payload.get("ordered_at")) or _now_iso_utc()

    if not patient_id:
        patient_id = username

    return {
        "patient_id": patient_id,
        "username": username or patient_id,
        "phone": phone,
        "medicine_name": medicine_name,
        "quantity": max(0, _to_int(payload.get("quantity"))),
        "dosage_frequency": dosage_frequency,
        "ordered_at": ordered_at,
        "unit_price": max(0.0, _to_float(payload.get("unit_price"), 0.0)),
        "total_price": max(0.0, _to_float(payload.get("total_price"), 0.0)),
        "source": _normalize_text(payload.get("source")) or "chat-confirmation",
        "status": _normalize_text(payload.get("status")) or "Placed",
    }


def append_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    record = _normalize_order_payload(payload or {})
    ORDER_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ORDER_HISTORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return record


def _iter_rows() -> Iterable[Dict[str, Any]]:
    if not ORDER_HISTORY_FILE.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with ORDER_HISTORY_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    rows.append(_normalize_order_payload(parsed))
            except json.JSONDecodeError:
                continue
    return rows


def list_orders(
    patient_id: Optional[str] = None,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = list(_iter_rows())

    patient_id_filter = _normalize_text(patient_id).lower()
    username_filter = _normalize_text(username).lower()
    phone_filter = _normalize_phone(phone)

    def _matches(row: Dict[str, Any]) -> bool:
        if patient_id_filter and _normalize_text(row.get("patient_id")).lower() != patient_id_filter:
            return False
        if username_filter and _normalize_text(row.get("username")).lower() != username_filter:
            return False
        if phone_filter and _normalize_phone(row.get("phone")) != phone_filter:
            return False
        return True

    filtered = [row for row in rows if _matches(row)]
    filtered.sort(key=lambda r: _normalize_text(r.get("ordered_at")), reverse=True)

    if isinstance(limit, int) and limit > 0:
        return filtered[:limit]
    return filtered


def latest_orders_by_patient_medicine() -> List[Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in _iter_rows():
        patient_id = _normalize_text(row.get("patient_id"))
        phone = _normalize_phone(row.get("phone"))
        medicine_name = _normalize_text(row.get("medicine_name"))
        if not patient_id or not phone or not medicine_name:
            continue
        key = f"{patient_id}|{medicine_name.lower()}"
        existing = latest.get(key)
        if not existing or _normalize_text(row.get("ordered_at")) > _normalize_text(existing.get("ordered_at")):
            latest[key] = row
    return list(latest.values())
