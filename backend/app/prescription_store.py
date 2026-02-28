import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEDICINE_DATA_FILE = DATA_DIR / "medicine_master.csv"
PRESCRIPTION_DIR = DATA_DIR / "prescriptions"
PRESCRIPTION_LOG_FILE = DATA_DIR / "prescription_submissions.jsonl"

MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower())
    return slug.strip("-") or "medicine"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())).strip()


def _extract_ocr_text(file_bytes: bytes) -> Dict[str, Any]:
    try:
        from orc.orc_service import extract_text_from_image
    except Exception as exc:
        return {"ok": False, "text": "", "error": f"OCR service unavailable: {exc}"}

    try:
        text = str(extract_text_from_image(file_bytes) or "").strip()
        if not text:
            return {"ok": False, "text": "", "error": "No text extracted from prescription image."}
        return {"ok": True, "text": text, "error": None}
    except Exception as exc:
        return {"ok": False, "text": "", "error": f"OCR extraction failed: {exc}"}


def _ocr_contains_medicine_name(ocr_text: str, medicine_name: str) -> bool:
    ocr_norm = _normalize_text(ocr_text)
    med_norm = _normalize_text(medicine_name)

    if not ocr_norm or not med_norm:
        return False

    if med_norm in ocr_norm:
        return True

    tokens = [t for t in med_norm.split() if len(t) >= 4]
    if not tokens:
        tokens = [t for t in med_norm.split() if len(t) >= 2]
    if not tokens:
        return False

    matched_tokens = sum(1 for t in tokens if t in ocr_norm)
    required_tokens = 1 if len(tokens) == 1 else min(2, len(tokens))
    return matched_tokens >= required_tokens


def _decode_image_data(image_data: str) -> tuple[bytes, str]:
    raw = (image_data or "").strip()
    if not raw:
        raise ValueError("Prescription photo is required.")

    mime_type = "application/octet-stream"
    payload = raw

    if raw.startswith("data:"):
        header, sep, body = raw.partition(",")
        if not sep:
            raise ValueError("Invalid prescription image format.")
        payload = body
        m = re.match(r"data:([^;]+);base64$", header, flags=re.IGNORECASE)
        if m:
            mime_type = m.group(1).strip().lower()

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ValueError("Invalid prescription image format.") from exc

    if not image_bytes:
        raise ValueError("Prescription image is empty.")

    return image_bytes, mime_type


def _lookup_medicine(medicine_name: str) -> Dict[str, Any]:
    if not MEDICINE_DATA_FILE.exists():
        return {
            "found": False,
            "matched_medicine_name": None,
            "prescription_required": False,
            "reason": "Medicine dataset not found.",
        }

    df = pd.read_csv(MEDICINE_DATA_FILE)
    match = df[df["medicine_name"].astype(str).str.contains(str(medicine_name), case=False, na=False)]

    if match.empty:
        return {
            "found": False,
            "matched_medicine_name": None,
            "prescription_required": False,
            "reason": f"Medicine '{medicine_name}' not found in dataset.",
        }

    row = match.iloc[0]
    matched = str(row.get("medicine_name", medicine_name)).strip()
    requires_rx = str(row.get("prescription_required", "")).strip().lower() == "yes"
    reason = (
        "Prescription requirement verified against dataset."
        if requires_rx
        else "This medicine does not require a prescription in dataset."
    )
    return {
        "found": True,
        "matched_medicine_name": matched,
        "prescription_required": requires_rx,
        "reason": reason,
    }


def save_and_verify_prescription(
    image_data: str,
    medicine_name: str,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    image_bytes, mime_type = _decode_image_data(image_data)
    lookup = _lookup_medicine(medicine_name)

    prescription_id = uuid.uuid4().hex
    ext = MIME_TO_EXT.get(mime_type, "jpg")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    med_slug = _sanitize_slug(lookup.get("matched_medicine_name") or medicine_name)

    PRESCRIPTION_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{ts}_{med_slug}_{prescription_id}.{ext}"
    stored_path = PRESCRIPTION_DIR / stored_name
    stored_path.write_bytes(image_bytes)

    sha256 = hashlib.sha256(image_bytes).hexdigest()
    ocr_result = _extract_ocr_text(image_bytes)
    ocr_text = str(ocr_result.get("text") or "")
    medicine_name_to_check = str(lookup.get("matched_medicine_name") or medicine_name).strip()
    name_present_in_prescription = _ocr_contains_medicine_name(ocr_text, medicine_name_to_check)

    verified = bool(
        lookup.get("found")
        and lookup.get("prescription_required")
        and ocr_result.get("ok")
        and name_present_in_prescription
    )
    verification_reason = lookup.get("reason")
    if not lookup.get("found"):
        verification_reason = lookup.get("reason")
    elif not lookup.get("prescription_required"):
        verification_reason = "This medicine does not require a prescription in dataset."
    elif not ocr_result.get("ok"):
        verification_reason = f"Prescription OCR failed: {ocr_result.get('error')}"
    elif not name_present_in_prescription:
        verification_reason = (
            f"Uploaded prescription does not contain medicine name '{medicine_name_to_check}'."
        )
    else:
        verification_reason = (
            f"Prescription verified. Found medicine name '{medicine_name_to_check}' in uploaded image."
        )

    record = {
        "id": prescription_id,
        "submitted_at": _utc_now_iso(),
        "medicine_name_requested": medicine_name,
        "medicine_name_matched": lookup.get("matched_medicine_name"),
        "prescription_required_in_dataset": bool(lookup.get("prescription_required")),
        "ocr_ok": bool(ocr_result.get("ok")),
        "ocr_error": ocr_result.get("error"),
        "ocr_text": ocr_text,
        "medicine_name_present_in_prescription": bool(name_present_in_prescription),
        "verified": verified,
        "verification_reason": verification_reason,
        "stored_file": str(stored_path),
        "original_filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(image_bytes),
        "sha256": sha256,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with PRESCRIPTION_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")

    return record
