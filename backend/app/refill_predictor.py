# Proactive refill recommendation module
import pandas as pd

history = pd.read_csv("order_history.csv")

def predict_refills():
    history["last_purchase_date"] = pd.to_datetime(history["last_purchase_date"])

    history["days_since"] = (
        pd.Timestamp.today() - history["last_purchase_date"]
    ).dt.days

    alerts = history[history["days_since"] > 20]

    return alerts[["customer_id", "medicine_name", "days_since"]]


if __name__ == "__main__":
    alerts = predict_refills()
    print("\n⚠️ Customers Needing Refill Soon:")
    print(alerts)
