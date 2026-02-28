import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "medicine_master.csv"
PRICE_XLSX_PATH = Path(__file__).resolve().parents[1] / "data" / "products-export.xlsx"
REFILL_AUDIT_PATH = Path(__file__).resolve().parents[1] / "data" / "refill_audit.jsonl"
DEFAULT_PRICE = 9.99
LOW_STOCK_THRESHOLD = 10
REFILL_TARGET_STOCK = 60


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_refill_audit(records):
    if not records:
        return

    REFILL_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REFILL_AUDIT_PATH.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def _auto_refill_low_stock(df: pd.DataFrame) -> pd.DataFrame:
    if "stock" not in df.columns or "medicine_name" not in df.columns:
        return df

    updated = df.copy()
    refill_records = []

    for idx, row in updated.iterrows():
        try:
            current_stock = int(row.get("stock", 0))
        except (TypeError, ValueError):
            current_stock = 0

        if current_stock < LOW_STOCK_THRESHOLD:
            new_stock = REFILL_TARGET_STOCK
            added = max(0, new_stock - current_stock)
            updated.loc[idx, "stock"] = new_stock

            refill_records.append(
                {
                    "timestamp": _utc_now_iso(),
                    "medicine_name": str(row.get("medicine_name", "")).strip(),
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                    "added_units": added,
                    "rule": f"stock < {LOW_STOCK_THRESHOLD} => refill to {REFILL_TARGET_STOCK}",
                }
            )

    if refill_records:
        updated.to_csv(DATA_PATH, index=False)
        _append_refill_audit(refill_records)

    return updated


def _read_refill_audit():
    if not REFILL_AUDIT_PATH.exists():
        return []

    rows = []
    with REFILL_AUDIT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    rows.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return rows


@router.get("/inventory")
def get_inventory():
    df = pd.read_csv(DATA_PATH)
    df = _auto_refill_low_stock(df)

    # Merge medicine prices from Excel (products-export.xlsx) using medicine/product name.
    if PRICE_XLSX_PATH.exists():
        prices_df = pd.read_excel(PRICE_XLSX_PATH, sheet_name="Products")
        if {"product name", "price rec"}.issubset(prices_df.columns):
            price_map = (
                prices_df[["product name", "price rec"]]
                .dropna(subset=["product name"])
                .assign(
                    key=lambda x: x["product name"].astype(str).str.strip(),
                    price=lambda x: pd.to_numeric(x["price rec"], errors="coerce"),
                )
                .drop(columns=["product name", "price rec"])
            )

            df = df.assign(key=df["medicine_name"].astype(str).str.strip()).merge(
                price_map,
                on="key",
                how="left",
            ).drop(columns=["key"])
            df = df.rename(columns={"price": "price"})

    if "price" not in df.columns:
        df["price"] = DEFAULT_PRICE
    else:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["price"] = df["price"].where(df["price"] > 0, DEFAULT_PRICE)
        df["price"] = df["price"].fillna(DEFAULT_PRICE)

    cols = ["medicine_name", "stock", "prescription_required", "price"]
    available_cols = [col for col in cols if col in df.columns]
    records = df[available_cols].to_dict(orient="records")
    return records


@router.get("/inventory/refill-log")
def get_refill_log():
    return _read_refill_audit()
