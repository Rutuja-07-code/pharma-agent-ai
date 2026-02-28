from datetime import datetime

try:
    from backend.app.history_data_loader import load_orders
    from backend.app.refill_predictor import calculate_refill_date
except ModuleNotFoundError:
    from history_data_loader import load_orders
    from refill_predictor import calculate_refill_date


def get_refill_dataframe(file_path):

    df = load_orders(file_path)

    df["next_refill_date"] = df.apply(
        lambda row: calculate_refill_date(
            row["purchase_date"],
            row["quantity"],
            row["dosage_frequency"]
        ),
        axis=1
    )

    return df


def get_due_refills(file_path):

    df = get_refill_dataframe(file_path)

    today = datetime.today().date()
    

    due = df[
        (df["next_refill_date"].notnull()) &
        (df["next_refill_date"].dt.date <= today)
    ]

    return due
