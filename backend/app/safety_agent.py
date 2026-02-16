# Prescription validation + stock rules
#done,worked

from pathlib import Path
import pandas as pd

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicine_master.csv"
df = pd.read_csv(DATA_FILE)


# Load medicine data
def safety_check(order):
    med = order.get("medicine_name")
    if not med:
        return {"status": "Rejected", "reason": "Missing medicine_name"}
    try:
        qty = int(order.get("quantity"))
    except (TypeError, ValueError):
        return {"status": "Rejected", "reason": "Invalid quantity"}

    # Find medicine
    match = df[df["medicine_name"].str.contains(med, case=False)]

    if match.empty:
        return {"status": "Rejected", "reason": "Medicine not found"}

    stock = int(match["stock"].values[0])
    prescription = match["prescription_required"].values[0]

    # Stock check
    if stock <= 0:
        return {
            "status": "Rejected",
            "reason": "Out of stock",
            "available_quantity": 0,
        }

    if stock < qty:
        return {
            "status": "Checking",
            "reason": f"Only {stock} units are available right now.But you requested{qty}",
            "available_quantity": stock,
        }

    # Prescription check
    if prescription == "Yes":
        return {"status": "Pending", "reason": "Prescription required before placing this order"}

    return {"status": "Approved", "reason": "Order allowed"}

from order_extractor import extract_order
from safety_agent import safety_check
from order_executor import place_order

# ✅ Temporary memory for pending order
pending_order = None


def pharmacy_chatbot(user_message):
    global pending_order

    user_message_lower = user_message.lower().strip()

    # ✅ Step A: Handle user confirmation for partial stock
    if pending_order is not None:

        # If user agrees
        if "yes" in user_message_lower or "order" in user_message_lower:

            # Place partial order
            confirmation = place_order(pending_order)

            # Clear pending order
            pending_order = None

            return (
                f"✅ Partial order placed successfully!\n\n"
                f"{confirmation}"
            )

        # If user says no
        if "no" in user_message_lower or "wait" in user_message_lower:

            pending_order = None
            return "Okay 👍 Order cancelled. Let me know if you need anything else."

        return "Please reply with 'Yes' to confirm partial order or 'No' to cancel."

    # ✅ Step 1: Extract order from user message
    order = extract_order(user_message)

    # ✅ Step 2: Safety check
    decision = safety_check(order)

    # Case 1: Rejected
    if decision["status"] == "Rejected":
        return f"❌ Order Rejected: {decision['reason']}"

    # Case 2: Prescription Pending
    if decision["status"] == "Pending":
        return f"⚠️ Prescription Required: {decision['reason']}"

    # Case 3: Partial stock available
    if decision["status"] == "Checking":

        available = decision["available_quantity"]

        # Save pending order with available qty
        pending_order = order
        pending_order["quantity"] = available

        return (
            f"⚠️ Stock Update:\n"
            f"{decision['reason']}\n\n"
            f"Would you like to order {available} units now?\n"
            f"Reply 'Yes' to confirm or 'No' to cancel."
        )

    # Case 4: Approved
    confirmation = place_order(order)
    return f"✅ Order Confirmed!\n{confirmation}"
