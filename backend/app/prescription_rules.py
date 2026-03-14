from __future__ import annotations

from typing import Any


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()

RX_VALUES = {"yes", "true", "1", "y", "rx", "prescription", "required"}
OTC_VALUES = {"no", "false", "0", "n", "otc", "non-rx", "not required", "optional"}


def prescription_required_for(medicine_name: Any, raw_value: Any) -> bool:
    raw = _normalize_text(raw_value)

    if raw in RX_VALUES:
        return True
    if raw in OTC_VALUES:
        return False
    return False


def prescription_label_for(medicine_name: Any, raw_value: Any) -> str:
    return "Yes" if prescription_required_for(medicine_name, raw_value) else "No"
