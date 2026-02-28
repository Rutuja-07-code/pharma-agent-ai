import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "medicine_master.csv"


def _load_inventory():
    # Read fresh CSV every time so latest stock changes are reflected.
    df = pd.read_csv(DATA_PATH)
    return df.rename(
        columns={
            "product name": "medicine_name",
            "prize": "price",
            "stock": "stock",
            "prescription_required": "prescription_required",
        }
    )

def search_medicine(query):
    df = _load_inventory()
    query = query.lower()

    # Find matches
    matches = df[df["medicine_name"].str.lower().str.contains(query, na=False)]

    if matches.empty:
        return {
            "status": "Not Found",
            "message": "Medicine not available in our inventory."
        }

    # Return top 3 matches with only available columns
    preferred_cols = [
        "medicine_name",
        "description",
        "dosage_info",
        "price",
        "stock",
        "prescription_required",
    ]
    available_cols = [col for col in preferred_cols if col in matches.columns]
    results = matches.head(3)[available_cols].to_dict(orient="records")

    return {
        "status": "Found",
        "results": results
    }


# Test
# if __name__ == "__main__":
#     print(search_medicine("dolo"))
