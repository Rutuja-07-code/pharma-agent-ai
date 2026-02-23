import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"


def _load_inventory():
    # Read fresh CSV every time so matching uses current inventory.
    return pd.read_csv(DATA_FILE)


def find_medicine_matches(user_med_name):
    """
    Returns:
    - None if no match
    - One medicine name if exact/single match
    - List of matches if multiple found
    """

    query = user_med_name.lower().strip()
    df = _load_inventory()

    matches = df[df["medicine_name"].str.lower().str.contains(query, na=False)]

    if matches.empty:
        return None

    # If only one match, return directly
    if len(matches) == 1:
        return matches.iloc[0]["medicine_name"]

    # If multiple matches, return list
    return matches["medicine_name"].head(5).tolist()
