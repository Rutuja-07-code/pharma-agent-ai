import pandas as pd

def load_orders(file_path):
    # The workbook has title rows before the real table header.
    df = pd.read_excel(file_path, header=4)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])

    return df
