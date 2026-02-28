import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
PRICE_FILE = Path(__file__).resolve().parent.parent / "data" / "products-export.xlsx"
DEFAULT_PRICE = 9.99


def _normalize_text(value):
    return str(value or "").strip().lower()


def _find_match(df, medicine_name):
    med_norm = _normalize_text(medicine_name)
    names_norm = df["medicine_name"].astype(str).str.strip().str.lower()

    exact_match = df[names_norm == med_norm]
    if not exact_match.empty:
        return exact_match

    return df[
        df["medicine_name"].astype(str).str.contains(
            str(medicine_name),
            case=False,
            na=False,
            regex=False,
        )
    ]


def _load_price_map():
    if not PRICE_FILE.exists():
        return {}
    try:
        prices_df = pd.read_excel(PRICE_FILE, sheet_name="Products")
        if not {"product name", "price rec"}.issubset(prices_df.columns):
            return {}

        price_map = {}
        for _, row in prices_df.iterrows():
            name = str(row.get("product name", "")).strip().lower()
            price = pd.to_numeric(row.get("price rec"), errors="coerce")
            if name and pd.notna(price):
                price_map[name] = float(price)
        return price_map
    except Exception:
        return {}


def _safe_unit_price(value):
    try:
        v = float(value)
        if v > 0:
            return v
    except Exception:
        pass
    return DEFAULT_PRICE


def quote_order(order):
    med = order["medicine_name"]
    qty = int(order["quantity"])
    if qty <= 0:
        return {"ok": False, "reason": "Quantity must be greater than 0."}

    df = pd.read_csv(DATA_FILE)
    match = _find_match(df, med)
    if match.empty:
        return {"ok": False, "reason": f"Medicine '{med}' not found in inventory."}

    idx = match.index[0]
    stock = int(df.loc[idx, "stock"])
    if stock <= 0:
        return {"ok": False, "reason": f"Cannot place order. '{med}' is out of stock."}
    if qty > stock:
        return {
            "ok": False,
            "reason": f"Only {stock} units are available. Please order {stock} or less.",
        }

    med_name = str(df.loc[idx, "medicine_name"]).strip()
    price_map = _load_price_map()
    unit_price = _safe_unit_price(price_map.get(med_name.lower(), 0.0))
    total_price = unit_price * qty

    return {
        "ok": True,
        "medicine_name": med_name,
        "quantity": qty,
        "unit_price": unit_price,
        "total_price": total_price,
    }


def place_order(order):
    med = order["medicine_name"]
    qty = int(order["quantity"])

    # Load fresh inventory for each order request.
    df = pd.read_csv(DATA_FILE)
    match = _find_match(df, med)

    if match.empty:
        return f"Medicine '{med}' not found in inventory."

    idx = match.index[0]
    med_name = str(df.loc[idx, "medicine_name"]).strip()
    stock = int(df.loc[idx, "stock"])

    if stock <= 0:
        return f"Cannot place order. '{med}' is out of stock."

    if qty > stock:
        return (
            f"Only {stock} units are available.\n"
            f"You requested {qty}.\n"
            f"Please order {stock} or less."
        )

    df.loc[idx, "stock"] = stock - qty
    df.to_csv(DATA_FILE, index=False)

    price_map = _load_price_map()
    unit_price = _safe_unit_price(price_map.get(med_name.lower(), 0.0))
    total_price = unit_price * qty

    return (
        "Order Confirmed!\n"
        f"Medicine: {med_name}\n"
        f"Quantity Ordered: {qty}\n"
        f"Unit Price: EUR {unit_price:.2f}\n"
        f"Total Price: EUR {total_price:.2f}\n"
    )


def refill_stock(medicine_name, refill_quantity=105):
    df = pd.read_csv(DATA_FILE)
    match = _find_match(df, medicine_name)

    if match.empty:
        return {"ok": False, "reason": f"Medicine '{medicine_name}' not found in inventory."}

    idx = match.index[0]
    med_name = str(df.loc[idx, "medicine_name"])
    current_stock = int(df.loc[idx, "stock"])
    added = int(refill_quantity)
    new_stock = current_stock + added

    df.loc[idx, "stock"] = new_stock
    df.to_csv(DATA_FILE, index=False)

    return {
        "ok": True,
        "medicine_name": med_name,
        "added": added,
        "new_stock": new_stock,
    }
