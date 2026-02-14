import pandas as pd

from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
df = pd.read_csv(DATA_FILE)

def place_order(order):
    med = order["medicine_name"]
    qty = order["quantity"]

    idx = df[df["medicine_name"].str.contains(med, case=False)].index[0]

    # Reduce stock
    df.loc[idx, "stock"] -= qty

    # Save updated inventory
    
    # df.to_csv("medicine_master.csv", index=False)
    df.to_csv(DATA_FILE, index=False)


    return "✅ Order Confirmed and Inventory Updated!"
