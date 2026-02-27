from fastapi import APIRouter
import pandas as pd
from pathlib import Path

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "medicine_master.csv"
PRICE_XLSX_PATH = Path(__file__).resolve().parents[1] / "data" / "products-export.xlsx"
DEFAULT_PRICE = 9.99

@router.get("/inventory")
def get_inventory():
    df = pd.read_csv(DATA_PATH)

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
