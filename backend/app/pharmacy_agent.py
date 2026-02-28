# # #End-to-end AI agent pipeline

# # from order_extractor import extract_order
# # from safety_agent import safety_check
# # from order_executor import place_order

# # #✅ Temporary memory for pending order
# # pending_order = None


# # def pharmacy_chatbot(user_message):
# #     global pending_order

# #     print("\n🧑 User:", user_message)
# #     user_message_lower = user_message.lower().strip()

# #     # ✅ Step A: Handle user confirmation for partial stock
# #     if pending_order is not None:

# #         # If user agrees
# #         if "yes" in user_message_lower or "order" in user_message_lower:

# #             # Place partial order
# #             confirmation = place_order(pending_order)

# #             # Clear pending order
# #             pending_order = None

# #             return (
# #                 f"✅ Partial order placed successfully!\n\n"
# #                 f"{confirmation}"
# #             )
# #         # If user says no
# #         if "no" in user_message_lower or "wait" in user_message_lower:

# #             pending_order = None
# #             return "Okay 👍 Order cancelled. Let me know if you need anything else."

# #         return "Please reply with 'Yes' to confirm partial order or 'No' to cancel."



# #     # Step 1: Extract order using LLM
# #     order = extract_order(user_message)
# #     print("🤖 Extracted Order:", order)
# #     if "error" in order:
# #         return f"❌ Could not understand order: {order['error']}"
# #     required = {"medicine_name", "quantity", "unit"}
# #     if not required.issubset(order.keys()):
# #         return f"❌ Could not understand order: missing fields {sorted(required - set(order.keys()))}"

# #     # Step 2: Safety Check
# #     decision = safety_check(order)
# #     print("🛡️ Safety Decision:", decision)

# #     if decision["status"] == "Rejected":
# #         return f"❌ Order Rejected: {decision['reason']}"
    
# #     if decision["status"] == "Pending":
# #         return f"Order Pending: {decision['reason']}"
    
# #     if decision["status"] == "Checking":

# #         available = decision["available_quantity"]

# #         # Save pending order with available qty
# #         pending_order = order
# #         pending_order["quantity"] = available

# #         return (
# #             f"⚠️ Stock Update:\n"
# #             f"{decision['reason']}\n\n"
# #             f"Would you like to order {available} units now?\n"
# #             f"Reply 'Yes' to confirm or 'No' to cancel."
# #         )


# #     # Step 3: Place Order
# #     confirmation = place_order(order)
# #     return confirmation


# # # Run chatbot
# # if __name__ == "__main__":
# #     msg = input("Enter medicine request: ")
# #     reply = pharmacy_chatbot(msg)
# #     print("\n🤖 Bot:", reply)


# # from order_extractor import extract_order
# # from safety_agent import safety_check
# # from order_executor import place_order

# # # ✅ Temporary memory
# # pending_order = None
# # pending_prescription_order = None


# # def pharmacy_chatbot(user_message):
# #     global pending_order
# #     global pending_prescription_order

# #     print("\n🧑 User:", user_message)
# #     user_message_lower = user_message.lower().strip()

# #     # ==========================================
# #     # ✅ STEP A: Handle Prescription Upload
# #     # ==========================================
# #     if pending_prescription_order is not None:

# #         if "upload" in user_message_lower or "done" in user_message_lower or "yes" in user_message_lower:

# #             # Place order after prescription upload
# #             confirmation = place_order(pending_prescription_order)

# #             pending_prescription_order = None

# #             return (
# #                 "✅ Prescription received successfully!\n"
# #                 f"{confirmation}"
# #             )

# #         return "⚠️ Please type 'upload prescription' to continue."

# #     # ==========================================
# #     # ✅ STEP B: Handle Partial Stock Confirmation
# #     # ==========================================
# #     if pending_order is not None:

# #         if "yes" in user_message_lower or "order" in user_message_lower:

# #             confirmation = place_order(pending_order)
# #             pending_order = None

# #             return (
# #                 f"✅ Partial order placed successfully!\n\n"
# #                 f"{confirmation}"
# #             )

# #         if "no" in user_message_lower or "wait" in user_message_lower:
# #             pending_order = None
# #             return "Okay 👍 Order cancelled."

# #         return "Please reply with 'Yes' or 'No'."

# #     # ==========================================
# #     # ✅ STEP 1: Extract Order
# #     # ==========================================
# #     order = extract_order(user_message)
# #     print("🤖 Extracted Order:", order)

# #     if "error" in order:
# #         return f"❌ Could not understand order: {order['error']}"

# #     required = {"medicine_name", "quantity", "unit"}
# #     if not required.issubset(order.keys()):
# #         return f"❌ Missing fields: {sorted(required - set(order.keys()))}"

# #     # ==========================================
# #     # ✅ STEP 2: Safety Check
# #     # ==========================================
# #     decision = safety_check(order)
# #     print("🛡️ Safety Decision:", decision)

# #     # Case 1: Rejected
# #     if decision["status"] == "Rejected":
# #         return f"❌ Order Rejected: {decision['reason']}"

# #     # Case 2: Prescription Required
# #     if decision["status"] == "Pending":

# #         pending_prescription_order = order

# #         return (
# #             f"⚠️ Prescription Required: {decision['reason']}\n\n"
# #             "Please type: 'upload prescription' to continue."
# #         )

# #     # Case 3: Partial Stock
# #     if decision["status"] == "Checking":

# #         available = decision["available_quantity"]

# #         pending_order = order
# #         pending_order["quantity"] = available

# #         return (
# #             f"⚠️ Stock Update:\n"
# #             f"{decision['reason']}\n\n"
# #             f"Would you like to order {available} units now?\n"
# #             f"Reply 'Yes' to confirm or 'No' to cancel."
# #         )

# #     # Case 4: Approved → Place Order
# #     confirmation = place_order(order)
# #     return f"✅ Order Confirmed!\n{confirmation}"

# from order_extractor import extract_order
# from safety_agent import safety_check
# from order_executor import place_order

# pending_prescription_order = None
# pending_final_quantity = None


# def pharmacy_chatbot(user_message):
#     global pending_prescription_order
#     global pending_final_quantity

#     msg = user_message.lower().strip()

#     # =========================================
#     # ✅ STEP A: Prescription Upload Handling
#     # =========================================
#     if pending_prescription_order is not None:

#         if "upload" in msg or "done" in msg or "yes" in msg:

#             # Prescription accepted → Place order
#             order = pending_prescription_order
#             order["quantity"] = pending_final_quantity

#             pending_prescription_order = None
#             pending_final_quantity = None

#             confirmation = place_order(order)

#             return (
#                 "✅ Prescription received successfully.\n"
#                 f"✅ Order placed for {order['quantity']} units.\n\n"
#                 f"{confirmation}"
#             )

#         return "⚠️ Please type 'upload prescription' to continue."

#     # =========================================
#     # ✅ STEP 1: Extract Order
#     # =========================================
#     order = extract_order(user_message)

#     if "error" in order:
#         return f"❌ Could not understand: {order['raw_output']}"

#     # =========================================
#     # ✅ STEP 2: Safety Check (Stock First)
#     # =========================================
#     decision = safety_check(order)

#     if decision["status"] == "Rejected":
#         return f"❌ {decision['reason']}"

#     stock = decision["stock"]
#     rx_required = decision["prescription_required"]

#     # =========================================
#     # ✅ STEP 3: Partial Stock Case
#     # =========================================
#     if decision["status"] == "Partial":

#         available = stock

#         # If prescription required → ask upload
#         if rx_required == "Yes":
#             pending_prescription_order = order
#             pending_final_quantity = available

#             return (
#                 f"⚠️ Stock Update: Only {available} units available.\n"
#                 f"⚠️ This medicine requires a prescription.\n\n"
#                 "Please type: 'upload prescription' to order available quantity."
#             )

#         # No prescription → place partial order directly
#         order["quantity"] = available
#         confirmation = place_order(order)

#         return (
#             f"⚠️ Only {available} units available.\n"
#             f"✅ Partial order placed successfully!\n\n"
#             f"{confirmation}"
#         )

#     # =========================================
#     # ✅ STEP 4: Full Stock Case
#     # =========================================
#     if decision["status"] == "InStock":

#         # If prescription required → ask upload
#         if rx_required == "Yes":
#             pending_prescription_order = order
#             pending_final_quantity = order["quantity"]

#             return (
#                 "⚠️ Prescription Required.\n"
#                 "Please type: 'upload prescription' to continue."
#             )

#         # No prescription → place order directly
#         confirmation = place_order(order)
#         return f"✅ Order Confirmed!\n\n{confirmation}"

"""
from order_extractor import extract_order
from safety_agent import safety_check
from order_executor import place_order, refill_stock, quote_order
from medicine_matcher import find_medicine_matches
from medicine_lookup import search_medicine
import re
from medicine_lookup import search_medicine
import re
from medicine_lookup import search_medicine
import re

pending_medicine_choice = None
pending_order_data = None


pending_prescription_order = None
pending_final_quantity = None
pending_stock_confirmation = False
pending_rx_confirmation = False



def pharmacy_chatbot(user_message):
    global pending_prescription_order
    global pending_final_quantity
    global pending_stock_confirmation

    msg = user_message.lower().strip()

    # =========================================
    # ✅ STEP A: After Prescription Upload → Ask Stock Confirmation
    # =========================================
    if pending_stock_confirmation:

        if msg in ["yes", "y", "order"]:
            order = pending_prescription_order
            order["quantity"] = pending_final_quantity

            confirmation = place_order(order)

            # Clear all pending states
            pending_prescription_order = None
            pending_final_quantity = None
            pending_stock_confirmation = False

            return (
                f"✅ Order placed successfully for {order['quantity']} units!\n\n"
                f"{confirmation}"
            )

        if msg in ["no", "n", "wait"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_stock_confirmation = False

            return "Okay 👍 Order cancelled."

        return "Please reply 'Yes' to confirm the order or 'No' to cancel."

    # =========================================
    # ✅ STEP B: Prescription Upload Handling
    # =========================================
    if pending_prescription_order is not None and not pending_stock_confirmation:
        if msg.lower() in ["yes", "y"]:
            # Prescription accepted → Now ask confirmation for stock
            pending_stock_confirmation = True
            return (
                f"✅ Prescription received.\n\n"
                f"⚠️ Only {pending_final_quantity} units are available.\n"
                f"Would you like to order {pending_final_quantity} units now?\n"
                f"Reply 'Yes' or 'No'."
            )
        elif msg.lower() in ["no", "n"]:
            pending_prescription_order = None
            pending_final_quantity = None
            return "❌ Order cannot be placed without a prescription."
        elif "upload prescription" in msg:
            # Simulate prescription upload and proceed to confirmation
            pending_stock_confirmation = True
            return (
                f"✅ Prescription received.\n\n"
                f"⚠️ Only {pending_final_quantity} units are available.\n"
                f"Would you like to order {pending_final_quantity} units now?\n"
                f"Reply 'Yes' or 'No'."
            )
        return "Do you have a prescription? (yes/no)"

    # =========================================
    # ✅ STEP 1: Extract Order
    # =========================================
    order = extract_order(user_message)

    if "error" in order:
        return f"❌ Could not understand: {order['raw_output']}"
    

    # =========================================
    # ✅ STEP 3: Medicine Name Matching
    # =========================================
    matches = find_medicine_matches(order["medicine_name"])

    if matches is None:
        return f"❌ Medicine '{order['medicine_name']}' not found in inventory."

    # If only one match → replace with full name
    if isinstance(matches, str):
        order["medicine_name"] = matches

    # If multiple matches → ask user to choose
    else:
        pending_medicine_choice = matches
        pending_order_data = order

        options = "\n".join(
            [f"{i+1}. {name}" for i, name in enumerate(matches)]
        )

        return (
            "⚠️ Multiple medicines found. Which one do you want?\n\n"
            f"{options}\n\n"
            "Reply with option number (1,2,3...)."
        )


    # =========================================
    # ✅ STEP 2: Safety Check
    # =========================================
    decision = safety_check(order)

    if decision["status"] == "Rejected":
        return f"❌ {decision['reason']}"

    stock = decision["stock"]
    rx_required = decision["prescription_required"]

    # =========================================
    # ✅ STEP 3: Partial Stock + Prescription Case
    # =========================================
    if decision["status"] == "Partial":

        available = stock

        if rx_required == "Yes":
            pending_prescription_order = order
            pending_final_quantity = available

            return (
                f"⚠️ Stock Update: Only {available} units available.\n"
                f"⚠️ Prescription is required.\n\n"
                "Do you have a prescription? (yes/no)"
            )

        # No prescription → place partial order directly
        order["quantity"] = available
        confirmation = place_order(order)

        return (
            f"⚠️ Only {available} units available.\n"
            f"✅ Partial order placed successfully!\n\n"
            f"{confirmation}"
        )

    # =========================================
    # ✅ STEP 4: Full Stock + Prescription Case
    # =========================================
    if decision["status"] == "InStock":

        if rx_required == "Yes":
            pending_prescription_order = order
            pending_final_quantity = order["quantity"]

            return (
                "⚠️ Prescription Required.\n"
                "Do you have a prescription? (yes/no)"
            )

        confirmation = place_order(order)
        return f"✅ Order Confirmed!\n\n{confirmation}"
"""

try:
    from backend.app.order_extractor import extract_order
    from backend.app.safety_agent import safety_check
    from backend.app.order_executor import place_order, quote_order
    from backend.app.medicine_matcher import find_medicine_matches
    from backend.app.medicine_lookup import search_medicine
except ModuleNotFoundError:
    from order_extractor import extract_order
    from safety_agent import safety_check
    from order_executor import place_order, quote_order
    from medicine_matcher import find_medicine_matches
    from medicine_lookup import search_medicine
import re

# ================================
# Pending States (Memory)
# ================================
pending_medicine_choice = None
pending_order_data = None

pending_prescription_order = None
pending_final_quantity = None

pending_rx_confirmation = False
pending_partial_after_rx = False
pending_partial_order = None
pending_partial_requires_rx = False
pending_preorder_offer = None


def _is_order_intent(message):
    msg = (message or "").lower()
    if re.search(r"\b\d+\b", msg):
        return True

    order_words = {
        "order",
        "buy",
        "need",
        "want",
        "refill",
        "book",
        "purchase",
    }
    quantity_units = {
        "strip",
        "strips",
        "tablet",
        "tablets",
        "bottle",
        "bottles",
        "unit",
        "units",
        "pack",
        "packs",
        "ml",
        "mg",
        "g",
    }

    words = set(re.findall(r"[a-zA-Z]+", msg))
    return bool(words.intersection(order_words) and words.intersection(quantity_units))


def _payment_required_response(order, context_message):
    quoted = quote_order(order)
    if not quoted.get("ok"):
        return f"Order cannot proceed: {quoted.get('reason', 'Unable to create payment request.')}"

    return {
        "type": "payment_required",
        "message": context_message,
        "payment": {
            "medicine_name": quoted["medicine_name"],
            "quantity": int(quoted["quantity"]),
            "unit_price": float(quoted["unit_price"]),
            "total_price": float(quoted["total_price"]),
            "currency": "INR",
        },
    }

def _extract_medicine_query(message):
    msg = (message or "").strip().lower()
    # Remove common intent filler so lookup uses medicine phrase.
    msg = re.sub(
        r"\b(i need|need|i want|want|show me|tell me about|do you have|check|search|for)\b",
        " ",
        msg,
    )
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg or (message or "").strip()


# ================================
# Main Chatbot Function
# ================================
def pharmacy_chatbot(user_message):
    global pending_medicine_choice
    global pending_order_data

    global pending_prescription_order
    global pending_final_quantity

    global pending_rx_confirmation
    global pending_partial_after_rx
    global pending_partial_order
    global pending_partial_requires_rx
    global pending_preorder_offer

    msg = (user_message or "").lower().strip()
    selected_order = None

    # Step 0: Out-of-stock pre-order confirmation
    if pending_preorder_offer is not None:
        medicine_name = pending_preorder_offer.get("medicine_name", "this medicine")
        refill_days = pending_preorder_offer.get("refill_days", "3-5")

        if msg in ["yes", "y", "confirm", "preorder", "pre-order"]:
            pending_preorder_offer = None
            return (
                f"Pre-order confirmed for {medicine_name}.\n"
                f"Expected refill in {refill_days} days.\n"
                "We will notify you when stock is refilled."
            )

        if msg in ["no", "n", "cancel", "wait"]:
            pending_preorder_offer = None
            return "Okay, pre-order cancelled."

        return "Do you want to place a pre-order? Reply 'Yes' or 'No'."

    # Step 1: Handle multiple medicine choice
    if pending_medicine_choice is not None:
        if not msg.isdigit():
            return "Please reply with option number (1,2,3...)."

        choice = int(msg)
        if not (1 <= choice <= len(pending_medicine_choice)):
            return "Invalid option number."

        selected_name = pending_medicine_choice[choice - 1]
        if not pending_order_data:
            pending_medicine_choice = None
            return "Previous order context expired. Please enter your request again."

        pending_order_data["medicine_name"] = selected_name
        pending_medicine_choice = None
        selected_order = pending_order_data
        pending_order_data = None

    # Step 2: Partial stock confirmation (before prescription)
    if pending_partial_order is not None:
        if msg in ["yes", "y", "confirm", "order"]:
            order = pending_partial_order

            if pending_partial_requires_rx:
                pending_prescription_order = order
                pending_final_quantity = int(order.get("quantity", 0))

                pending_partial_order = None
                pending_partial_requires_rx = False
                pending_rx_confirmation = False
                pending_partial_after_rx = True

                return "This medicine requires a prescription. Do you have a prescription? (yes/no)"

            pending_partial_order = None
            pending_partial_requires_rx = False
            return _payment_required_response(
                order,
                (
                    f"Partial stock confirmed for {order['quantity']} units.\n"
                    "Proceed to test payment to place this order."
                ),
            )

        if msg in ["no", "n", "cancel", "wait"]:
            pending_partial_order = None
            pending_partial_requires_rx = False
            return "Okay, order cancelled."

        return "Only limited stock is available. Reply 'Yes' to order available quantity or 'No' to cancel."

    # Step 3: Final confirmation after prescription upload
    if pending_rx_confirmation:
        if msg in ["yes", "y", "confirm"]:
            order = pending_prescription_order
            order["quantity"] = pending_final_quantity

            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False

            return _payment_required_response(
                order,
                "Prescription and stock confirmed. Proceed to test payment to place your order.",
            )

        if msg in ["no", "n", "cancel"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            return "Okay, order cancelled."

        return "Please reply 'Yes' to confirm or 'No' to cancel."

    # Step 4: Prescription confirmation handling
    if pending_prescription_order is not None and not pending_rx_confirmation:
        if msg in ["yes", "y", "upload", "done", "upload prescription"]:
            requested_qty = int(pending_prescription_order.get("quantity", pending_final_quantity or 0))
            final_qty = int(pending_final_quantity or requested_qty)

            current_order = dict(pending_prescription_order)
            current_order["quantity"] = final_qty
            latest_decision = safety_check(current_order)

            if latest_decision["status"] == "Rejected":
                reason = str(latest_decision.get("reason", "Order rejected"))
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                if "out of stock" in reason.lower():
                    pending_preorder_offer = {
                        "medicine_name": current_order.get("medicine_name"),
                        "refill_days": "3-5",
                    }
                    return (
                        f"Order Rejected: {reason}.\n"
                        "This medicine is currently out of stock.\n"
                        "Expected refill in 3-5 days.\n"
                        "Do you want to place a pre-order? (yes/no)"
                    )
                return f"Order Rejected: {reason}"

            order = pending_prescription_order
            if latest_decision["status"] == "Partial":
                order["quantity"] = int(latest_decision["stock"])
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                return _payment_required_response(
                    order,
                    (
                        f"Only {order['quantity']} units are available (you requested {requested_qty}).\n"
                        "Proceed to test payment to place the partial order."
                    ),
                )

            order["quantity"] = final_qty
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            return _payment_required_response(
                order,
                "Prescription verified. Proceed to test payment to place your order.",
            )

        if msg in ["no", "n", "cancel"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            return "Okay, order cancelled because prescription is required."

        return "Do you have a prescription? (yes/no)"

    # Step 5: Info mode (no order intent)
    if selected_order is None and not _is_order_intent(user_message):
        lookup_query = _extract_medicine_query(user_message)
        lookup = search_medicine(lookup_query)
        if lookup.get("status") != "Found":
            # Fallback: if sentence lookup still fails, attempt order extraction and lookup by medicine name.
            extracted = extract_order(user_message)
            med_name = extracted.get("medicine_name") if isinstance(extracted, dict) else None
            if med_name:
                lookup = search_medicine(med_name)
            if lookup.get("status") != "Found":
                return f"❌ {lookup.get('message', 'Medicine not available in our inventory.')}"

        rows = lookup.get("results", [])
        lines = []
        for row in rows:
            name = row.get("medicine_name", "Unknown")
            stock = row.get("stock", "NA")
            rx = row.get("prescription_required", "NA")
            lines.append(f"- {name} | Stock: {stock} | Prescription: {rx}")
        return "Medicine Info:\n" + "\n".join(lines)

    # Step 6: Extract order (LLM)
    if selected_order is None:
        order = extract_order(user_message)

        if "error" in order:
            err = order.get("error")
            raw = order.get("raw_output")
            if err and "LLM service unavailable" in err:
                return (
                    "Sorry, our order extraction service is temporarily unavailable. "
                    "Please try again later or contact support if the problem persists."
                )
            if raw:
                return f"Could not understand your request.\nError: {err}\nRaw Output: {raw}"
            return f"Could not understand your request.\nError: {err}"

        required_fields = {"medicine_name", "quantity", "unit"}
        if not required_fields.issubset(order.keys()):
            return f"Missing fields: {required_fields - set(order.keys())}"
    else:
        order = selected_order

    # Step 7: Medicine name matching
    if selected_order is None:
        matches = find_medicine_matches(order["medicine_name"])

        if matches is None:
            return f"Medicine '{order['medicine_name']}' not found in inventory."

        if isinstance(matches, str):
            order["medicine_name"] = matches
        else:
            pending_medicine_choice = matches
            pending_order_data = order
            options = "\n".join([f"{i+1}. {name}" for i, name in enumerate(matches)])
            return (
                "Multiple medicines found. Which one do you want?\n\n"
                f"{options}\n\n"
                "Reply with option number (1,2,3...)."
            )

    # Step 8: Safety check (stock + prescription)
    decision = safety_check(order)

    if decision["status"] == "Rejected":
        reason = str(decision.get("reason", "Order rejected"))
        if "out of stock" in reason.lower():
            pending_preorder_offer = {
                "medicine_name": order.get("medicine_name"),
                "refill_days": "3-5",
            }
            return (
                f"Order Rejected: {reason}.\n"
                "This medicine is currently out of stock.\n"
                "Expected refill in 3-5 days.\n"
                "Do you want to place a pre-order? (yes/no)"
            )
        return f"Order Rejected: {reason}"

    stock = decision["stock"]
    rx_required = str(decision["prescription_required"]).strip().lower() == "yes"

    # Step 9: Partial stock case
    if decision["status"] == "Partial":
        available = stock
        partial_order = dict(order)
        partial_order["quantity"] = available

        pending_partial_order = partial_order
        pending_partial_requires_rx = rx_required
        pending_partial_after_rx = False

        return (
            f"Stock Update: Only {available} units are available (you requested {decision.get('requested', order.get('quantity'))}).\n"
            f"Would you like to order {available} units?\n"
            "Reply 'Yes' to continue or 'No' to cancel."
        )

    # Step 10: Full stock case
    if decision["status"] == "InStock":
        if rx_required:
            pending_prescription_order = order
            pending_final_quantity = order["quantity"]
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            return "Prescription Required. Do you have a prescription? (yes/no)"

        return _payment_required_response(
            order,
            "Stock available. Proceed to test payment to place your order.",
        )
