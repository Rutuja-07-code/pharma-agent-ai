import pandas as pd
from pathlib import Path
from datetime import datetime
import uuid
import csv

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
PRICE_FILE = Path(__file__).resolve().parent.parent / "data" / "products-export.xlsx"
ORDER_HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "Consumer Order History 1.xlsx"
CONTACTS_FILE = Path(__file__).resolve().parent.parent / "data" / "patient_contacts.csv"
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


def place_order(order, user_id="GUEST", phone=None):
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
    prescription_req = str(df.loc[idx, "prescription_required"]).lower() == "true"

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

    _save_order_to_history(user_id, med_name, qty, total_price, prescription_req)
    
    if phone:
        _update_user_contact(user_id, phone)

    return (
        "Order Confirmed!\n"
        f"Medicine: {med_name}\n"
        f"Quantity Ordered: {qty}\n"
        f"Unit Price: EUR {unit_price:.2f}\n"
        f"Total Price: EUR {total_price:.2f}\n"
    )


def _save_order_to_history(user_id, product_name, quantity, total_price, prescription_required):
    try:
        if ORDER_HISTORY_FILE.exists():
            df = pd.read_excel(ORDER_HISTORY_FILE, header=4)
        else:
            df = pd.DataFrame(columns=[
                'Patient ID', 'Patient Age', 'Patient Gender', 'Purchase Date',
                'Product Name', 'Quantity', 'Total Price (EUR)', 
                'Dosage Frequency', 'Prescription Required'
            ])
        
        new_order = {
            'Patient ID': user_id,
            'Patient Age': None,
            'Patient Gender': None,
            'Purchase Date': datetime.now(),
            'Product Name': product_name,
            'Quantity': quantity,
            'Total Price (EUR)': total_price,
            'Dosage Frequency': None,
            'Prescription Required': 'Yes' if prescription_required else 'No'
        }
        
        df = pd.concat([df, pd.DataFrame([new_order])], ignore_index=True)
        
        with pd.ExcelWriter(ORDER_HISTORY_FILE, engine='openpyxl') as writer:
            empty_df = pd.DataFrame([[''], [''], [''], ['']])
            empty_df.to_excel(writer, index=False, header=False, startrow=0)
            df.to_excel(writer, index=False, startrow=4)
    except Exception as e:
        print(f"Failed to save order to history: {e}")


def _update_user_contact(user_id, phone):
    try:
        print(f"Updating contact for user_id={user_id}, phone={phone}")
        if CONTACTS_FILE.exists():
            df = pd.read_csv(CONTACTS_FILE)
        else:
            df = pd.DataFrame(columns=['patient_id', 'email', 'phone', 'whatsapp', 'last_purchase_date', 'days_supply'])
        
        if user_id in df['patient_id'].values:
            df.loc[df['patient_id'] == user_id, 'phone'] = phone
            df.loc[df['patient_id'] == user_id, 'last_purchase_date'] = datetime.now().date()
            print(f"Updated existing contact for {user_id}")
        else:
            new_contact = {
                'patient_id': user_id,
                'email': f"{user_id.lower()}@example.com",
                'phone': phone,
                'whatsapp': phone,
                'last_purchase_date': datetime.now().date(),
                'days_supply': 30
            }
            df = pd.concat([df, pd.DataFrame([new_contact])], ignore_index=True)
            print(f"Added new contact for {user_id}")
        
        df.to_csv(CONTACTS_FILE, index=False)
        print(f"Contact file saved successfully")
    except Exception as e:
        print(f"Failed to update user contact: {e}")


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
