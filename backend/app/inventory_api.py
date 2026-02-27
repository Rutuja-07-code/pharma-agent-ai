from fastapi import APIRouter
import pandas as pd
from pathlib import Path

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "medicine_master.csv"

@router.get("/inventory")
def get_inventory():
    df = pd.read_csv(DATA_PATH)
    # Only return relevant columns for dashboard
    cols = ["medicine_name", "stock", "prescription_required"]
    available_cols = [col for col in cols if col in df.columns]
    return df[available_cols].to_dict(orient="records")
