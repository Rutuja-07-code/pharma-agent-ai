import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"

df = pd.read_csv(DATA_FILE)


def find_medicine_matches(user_med_name):
    """
    Returns:
    - None if no match
    - One medicine name if exact/single match
    - List of matches if multiple found
    """

    query = user_med_name.lower().strip()

    matches = df[df["medicine_name"].str.lower().str.contains(query)]

    if matches.empty:
        return None

    # If only one match, return directly
    if len(matches) == 1:
        return matches.iloc[0]["medicine_name"]

    # If multiple matches, return list
    return matches["medicine_name"].head(5).tolist()
