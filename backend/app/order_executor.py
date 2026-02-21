# import pandas as pd

# from pathlib import Path

# DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
# df = pd.read_csv(DATA_FILE)

# def place_order(order):
#     med = order["medicine_name"]
#     qty = order["quantity"]

#     idx = df[df["medicine_name"].str.contains(med, case=False)].index[0]

#     # Reduce stock
#     df.loc[idx, "stock"] -= qty
#     # Save updated inventory
    
#     # df.to_csv("medicine_master.csv", index=False)
#     df.to_csv(DATA_FILE, index=False)


#     return "✅ Order Confirmed and Inventory Updated!"

import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"


def place_order(order):
    med = order["medicine_name"]
    qty = int(order["quantity"])

    # ✅ Load fresh inventory every time
    df = pd.read_csv(DATA_FILE)

    # ✅ Find medicine safely
    match = df[df["medicine_name"].str.contains(med, case=False)]

    if match.empty:
        return f"❌ Medicine '{med}' not found in inventory."

    idx = match.index[0]
    stock = int(df.loc[idx, "stock"])

    # ✅ Block if stock is zero
    if stock <= 0:
        return f"❌ Cannot place order. '{med}' is out of stock."

    # ✅ Block if quantity exceeds stock
    if qty > stock:
        return (
            f"⚠️ Only {stock} units are available.\n"
            f"You requested {qty}.\n"
            f"Please order {stock} or less."
        )

    # ✅ Safe stock deduction
    df.loc[idx, "stock"] = stock - qty

    # ✅ Save updated inventory
    df.to_csv(DATA_FILE, index=False)

    return (
        f"✅ Order Confirmed!\n"
        f"Medicine: {med}\n"
        f"Quantity Ordered: {qty}\n"
        # f"Remaining Stock: {df.loc[idx, 'stock']}"
    )
