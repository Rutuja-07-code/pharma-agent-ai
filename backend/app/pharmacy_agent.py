#End-to-end AI agent pipeline

from order_extractor import extract_order
from safety_agent import safety_check
from order_executor import place_order


def pharmacy_chatbot(user_message):

    print("\n🧑 User:", user_message)

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

    # Step 3: Place Order
    confirmation = place_order(order)
    return confirmation


# Run chatbot
if __name__ == "__main__":
    msg = input("Enter medicine request: ")
    reply = pharmacy_chatbot(msg)
    print("\n🤖 Bot:", reply)
