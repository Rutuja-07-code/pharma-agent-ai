#End-to-end AI agent pipeline

from order_extractor import extract_order
from safety_agent import safety_check
from order_executor import place_order

#✅ Temporary memory for pending order
pending_order = None


def pharmacy_chatbot(user_message):
    global pending_order

    print("\n🧑 User:", user_message)
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



    # Step 1: Extract order using LLM
    order = extract_order(user_message)
    print("🤖 Extracted Order:", order)
    if "error" in order:
        return f"❌ Could not understand order: {order['error']}"
    required = {"medicine_name", "quantity", "unit"}
    if not required.issubset(order.keys()):
        return f"❌ Could not understand order: missing fields {sorted(required - set(order.keys()))}"

    # Step 2: Safety Check
    decision = safety_check(order)
    print("🛡️ Safety Decision:", decision)

    if decision["status"] == "Rejected":
        return f"❌ Order Rejected: {decision['reason']}"
    
    if decision["status"] == "Pending":
        return f"Order Pending: {decision['reason']}"
    
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


    # Step 3: Place Order
    confirmation = place_order(order)
    return confirmation


# Run chatbot
if __name__ == "__main__":
    msg = input("Enter medicine request: ")
    reply = pharmacy_chatbot(msg)
    print("\n🤖 Bot:", reply)

