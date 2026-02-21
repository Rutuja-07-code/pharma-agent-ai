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
from order_executor import place_order
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

        if "upload" in msg or "done" in msg:

            # Prescription accepted → Now ask confirmation for stock
            pending_stock_confirmation = True

            return (
                f"✅ Prescription received.\n\n"
                f"⚠️ Only {pending_final_quantity} units are available.\n"
                f"Would you like to order {pending_final_quantity} units now?\n"
                f"Reply 'Yes' or 'No'."
            )

        return "⚠️ Please type 'upload prescription' to continue."

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
                "Please type: 'upload prescription' to continue."
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
                "Please type: 'upload prescription' to continue."
            )

        confirmation = place_order(order)
        return f"✅ Order Confirmed!\n\n{confirmation}"
"""

from order_extractor import extract_order
from safety_agent import safety_check
from order_executor import place_order
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

    msg = user_message.lower().strip()
    selected_order = None

    # =========================================
    # ✅ STEP 0: Handle Multiple Medicine Choice
    # =========================================
    if pending_medicine_choice is not None:
        if not msg.isdigit():
            return "Please reply with option number (1,2,3...)."

        choice = int(msg)
        if not (1 <= choice <= len(pending_medicine_choice)):
            return "❌ Invalid option number."

        selected_name = pending_medicine_choice[choice - 1]
        if not pending_order_data:
            pending_medicine_choice = None
            return "❌ Previous order context expired. Please enter your request again."

        # Update order medicine name
        pending_order_data["medicine_name"] = selected_name

        # Clear choice state
        pending_medicine_choice = None

        # Continue processing
        selected_order = pending_order_data
        pending_order_data = None

    # =========================================
    # ✅ STEP 1: Final Confirmation After Prescription Upload
    # =========================================
    if pending_rx_confirmation:

        if msg in ["yes", "y", "confirm"]:
            order = pending_prescription_order
            order["quantity"] = pending_final_quantity

            confirmation = place_order(order)

            # Clear all pending states
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False

            return f"✅ Order Confirmed!\n\n{confirmation}"

        if msg in ["no", "n", "cancel"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False

            return "Okay 👍 Order cancelled."

        return "Please reply 'Yes' to confirm or 'No' to cancel."

    # =========================================
    # ✅ STEP 2: Prescription Upload Handling
    # =========================================
    if pending_prescription_order is not None and not pending_rx_confirmation:

        if "upload" in msg or "done" in msg:
            requested_qty = int(pending_prescription_order.get("quantity", pending_final_quantity or 0))
            final_qty = int(pending_final_quantity or 0)

            # Re-check safety now to avoid stale stock/prescription state.
            current_order = dict(pending_prescription_order)
            current_order["quantity"] = final_qty
            latest_decision = safety_check(current_order)

            if latest_decision["status"] == "Rejected":
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                return f"❌ Order Rejected: {latest_decision['reason']}"

            if latest_decision["status"] == "Partial":
                final_qty = int(latest_decision["stock"])
                pending_final_quantity = final_qty
                pending_rx_confirmation = True
                return (
                    "✅ Prescription received successfully.\n\n"
                    f"⚠️ Only {final_qty} units are available (you requested {requested_qty}).\n"
                    "Would you like to confirm the partial order?\n"
                    "Reply 'Yes' to confirm or 'No' to cancel."
                )

            order = pending_prescription_order
            order["quantity"] = final_qty
            confirmation = place_order(order)

            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False

            return f"✅ Prescription received.\n\n{confirmation}"

        return "⚠️ Please type 'upload prescription' to continue."

    # =========================================
    # ✅ STEP 3: Info Mode (no order intent)
    # =========================================
    if selected_order is None and not _is_order_intent(user_message):
        lookup = search_medicine(user_message)
        if lookup.get("status") != "Found":
            return f"❌ {lookup.get('message', 'Medicine not available in our inventory.')}"

        rows = lookup.get("results", [])
        lines = []
        for row in rows:
            name = row.get("medicine_name", "Unknown")
            stock = row.get("stock", "NA")
            rx = row.get("prescription_required", "NA")
            lines.append(f"- {name} | Stock: {stock} | Prescription: {rx}")
        return "🔎 Medicine Info:\n" + "\n".join(lines)

    # =========================================
    # ✅ STEP 4: Extract Order (LLM)
    # =========================================
    if selected_order is None:
        order = extract_order(user_message)

        if "error" in order:
            return f"❌ Could not understand your request.\nRaw Output: {order['raw_output']}"

        required_fields = {"medicine_name", "quantity", "unit"}
        if not required_fields.issubset(order.keys()):
            return f"❌ Missing fields: {required_fields - set(order.keys())}"
    else:
        order = selected_order

    # =========================================
    # ✅ STEP 5: Medicine Name Matching
    # =========================================
    if selected_order is None:
        matches = find_medicine_matches(order["medicine_name"])

        if matches is None:
            return f"❌ Medicine '{order['medicine_name']}' not found in inventory."

        # Single match → replace with full name
        if isinstance(matches, str):
            order["medicine_name"] = matches

        # Multiple matches → ask user choice
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
    # ✅ STEP 6: Safety Check (Stock + Prescription)
    # =========================================
    decision = safety_check(order)

    if decision["status"] == "Rejected":
        return f"❌ Order Rejected: {decision['reason']}"

    stock = decision["stock"]
    rx_required = str(decision["prescription_required"]).strip().lower() == "yes"

    # =========================================
    # ✅ STEP 7: Partial Stock Case
    # =========================================
    if decision["status"] == "Partial":

        available = stock

        # Prescription required → upload first
        if rx_required:
            pending_prescription_order = order
            pending_final_quantity = available
            pending_rx_confirmation = False
            pending_partial_after_rx = True

            return (
                f"⚠️ Stock Update: Only {available} units available.Do you want to order\n"
                f"⚠️ This medicine requires a prescription.\n\n"
                "Please type: 'upload prescription' to continue."
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
    # ✅ STEP 8: Full Stock Case
    # =========================================
    if decision["status"] == "InStock":

        # Prescription required
        if rx_required:
            pending_prescription_order = order
            pending_final_quantity = order["quantity"]
            pending_rx_confirmation = False
            pending_partial_after_rx = False

            return (
                "⚠️ Prescription Required.\n"
                "Please type: 'upload prescription' to continue."
            )

        # Normal medicine → place order
        confirmation = place_order(order)
        return f"✅ Order Confirmed!\n\n{confirmation}"
