# # #End-to-end AI agent pipeline
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
import os
import requests
from typing import Optional, Dict, Any, Callable

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
pending_prescription_upload: Optional[Dict[str, Any]] = None
conversation_context: Dict[str, Dict[str, Any]] = {}
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL") or os.getenv("OLLAMA_MODEL") or "phi"
OLLAMA_CHAT_STYLE = os.getenv("OLLAMA_CHAT_STYLE", "friendly")
MAX_FRIENDLY_REPLY_CHARS = 280


def get_pending_prescription_context():
    if pending_prescription_order is None:
        return None

    return {
        "medicine_name": str(pending_prescription_order.get("medicine_name", "")).strip(),
        "quantity": int(pending_final_quantity or pending_prescription_order.get("quantity") or 0),
    }


def set_prescription_upload_verification(upload_record: Dict[str, Any]):
    global pending_prescription_upload
    pending_prescription_upload = dict(upload_record or {})


def _clear_prescription_upload():
    global pending_prescription_upload
    pending_prescription_upload = None


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


def _prescription_required_response(context_message):
    return {
        "type": "prescription_required",
        "message": context_message,
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


def _is_medicine_lookup_intent(message: str) -> bool:
    msg = str(message or "").strip().lower()
    if not msg:
        return False

    lookup_keywords = {
        "medicine",
        "medicines",
        "stock",
        "available",
        "availability",
        "price",
        "cost",
        "dosage",
        "tablet",
        "tablets",
        "capsule",
        "capsules",
        "syrup",
        "ml",
        "mg",
    }
    words = set(re.findall(r"[a-zA-Z]+", msg))
    return bool(words.intersection(lookup_keywords))


def _friendly_chat_reply(user_message: str) -> Optional[str]:
    system_prompt = (
        f"You are Medico, a {OLLAMA_CHAT_STYLE} and helpful AI pharmacy assistant. "
        "Write in simple, human language. Keep a warm tone, never robotic. "
        "Keep every answer concise: maximum 2 short sentences. "
        "Do not generate stories, puzzles, role-play, or long explanations. "
        "For health questions, be careful and practical. If risk is high, suggest seeing a doctor. "
        "Ask one short follow-up question when details are missing. "
        "If the user message is empty, respond gently and invite them to ask anything about "
        "medicines, symptoms, refills, or placing orders. "
        "Do not output JSON unless explicitly requested."
    )

    content = str(user_message or "").strip()
    if not content:
        content = "(empty input)"

    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": OLLAMA_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 90},
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        text = str(payload.get("message", {}).get("content", "")).strip()
        if not text:
            return None

        # Hard guardrail: keep output short even if model ignores instructions.
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(sentences[:2]).strip()
        if len(text) > MAX_FRIENDLY_REPLY_CHARS:
            text = text[:MAX_FRIENDLY_REPLY_CHARS].rstrip(" ,;:-") + "."
        return text
    except requests.RequestException:
        return None


def _resolve_context_key(chat_id: Optional[str], user_id: Optional[str], phone: Optional[str]) -> str:
    if chat_id:
        return f"chat:{str(chat_id).strip()}"
    if phone:
        return f"phone:{str(phone).strip()}"
    if user_id:
        return f"user:{str(user_id).strip()}"
    return "global"


def _get_context_bucket(context_key: str) -> Dict[str, Any]:
    bucket = conversation_context.get(context_key)
    if not isinstance(bucket, dict):
        bucket = {}
        conversation_context[context_key] = bucket
    return bucket


def _extract_quantity_and_unit_from_message(message: str, fallback_unit: str = "strip") -> Dict[str, Any]:
    msg = str(message or "").lower()
    qty_match = re.search(r"\b(\d+)\b", msg)
    quantity = int(qty_match.group(1)) if qty_match else None

    unit_aliases = {
        "strip": "strip",
        "strips": "strip",
        "tablet": "tablet",
        "tablets": "tablet",
        "capsule": "capsule",
        "capsules": "capsule",
        "bottle": "bottle",
        "bottles": "bottle",
        "pack": "pack",
        "packs": "pack",
        "unit": "unit",
        "units": "unit",
    }
    words = re.findall(r"[a-zA-Z]+", msg)
    unit = next((unit_aliases[w] for w in words if w in unit_aliases), None)

    return {
        "quantity": quantity,
        "unit": unit or fallback_unit or "strip",
    }


def _looks_like_followup_quantity_message(message: str) -> bool:
    msg = str(message or "").strip().lower()
    if not msg:
        return False
    if not re.search(r"\b\d+\b", msg):
        return False
    words = re.findall(r"[a-zA-Z]+", msg)
    if len(words) <= 4:
        return True
    followup_terms = {"need", "want", "order", "buy", "refill", "take", "require"}
    return bool(set(words).intersection(followup_terms))


def _is_no_prescription_message(message: str) -> bool:
    msg = str(message or "").strip().lower()
    if not msg:
        return False
    no_terms = [
        "don't have prescription",
        "dont have prescription",
        "do not have prescription",
        "no prescription",
        "without prescription",
        "no rx",
    ]
    return any(term in msg for term in no_terms)


AgentTracer = Optional[Callable[[str, Dict[str, Any], Dict[str, Any], str], None]]


def _trace_agent(
    trace: AgentTracer,
    agent_name: str,
    input_payload: Optional[Dict[str, Any]] = None,
    output_payload: Optional[Dict[str, Any]] = None,
    status: str = "ok",
):
    if not callable(trace):
        return
    try:
        trace(
            agent_name,
            dict(input_payload or {}),
            dict(output_payload or {}),
            status,
        )
    except Exception:
        # Tracing should never break the order flow.
        return


def _execute_order_with_agent_traces(
    order: Dict[str, Any],
    trace: AgentTracer = None,
    stock_before: Optional[int] = None,
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
):
    qty = int(order.get("quantity", 0) or 0)
    med_name = str(order.get("medicine_name", "")).strip()

    if stock_before is not None:
        _trace_agent(
            trace,
            "Inventory Agent",
            input_payload={
                "medicine_name": med_name,
                "requested_quantity": qty,
            },
            output_payload={
                "stock_available": int(stock_before),
                "reserved_quantity": qty,
            },
        )

    confirmation = place_order(order, user_id=user_id or "GUEST", phone=phone)
    is_success = "Order Confirmed!" in str(confirmation)
    _trace_agent(
        trace,
        "Execution Agent",
        input_payload={
            "medicine_name": med_name,
            "quantity": qty,
        },
        output_payload={
            "success": is_success,
            "confirmation": str(confirmation),
        },
        status="ok" if is_success else "error",
    )

    if stock_before is not None:
        remaining = max(0, int(stock_before) - qty)
        procurement_threshold = 10
        action = (
            "No action"
            if remaining > procurement_threshold
            else "Create refill task"
        )
        _trace_agent(
            trace,
            "Procurement Agent",
            input_payload={
                "medicine_name": med_name,
                "remaining_stock": remaining,
                "threshold": procurement_threshold,
            },
            output_payload={"action": action},
        )

    return confirmation


# ================================
# Main Chatbot Function
# ================================
def pharmacy_chatbot(
    user_message,
    trace: AgentTracer = None,
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    chat_id: Optional[str] = None,
):
    global pending_medicine_choice
    global pending_order_data

    global pending_prescription_order
    global pending_final_quantity

    global pending_rx_confirmation
    global pending_partial_after_rx
    global pending_partial_order
    global pending_partial_requires_rx
    global pending_preorder_offer
    global pending_prescription_upload

    msg = (user_message or "").lower().strip()
    selected_order = None
    context_key = _resolve_context_key(chat_id=chat_id, user_id=user_id, phone=phone)
    context = _get_context_bucket(context_key)

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
        context["last_medicine_name"] = selected_name
        context["last_unit"] = str(selected_order.get("unit") or context.get("last_unit") or "strip")
        _trace_agent(
            trace,
            "Intent Agent",
            input_payload={"selection": choice, "user_message": user_message},
            output_payload=dict(selected_order),
        )

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
                _clear_prescription_upload()

                return _prescription_required_response(
                    "This medicine requires a prescription.\n"
                    "Please click 'Add Prescription' and upload a clear photo to continue."
                )

            confirmation = _execute_order_with_agent_traces(
                order,
                trace=trace,
                stock_before=int(order.get("quantity", 0) or 0),
                user_id=user_id,
                phone=phone,
            )
            pending_partial_order = None
            pending_partial_requires_rx = False
            return (
                f"Partial stock confirmed for {order['quantity']} units.\n"
                f"{confirmation}"
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

            confirmation = _execute_order_with_agent_traces(order, trace=trace, user_id=user_id, phone=phone)
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            _clear_prescription_upload()

            return (
                "Prescription and stock confirmed.\n"
                f"{confirmation}"
            )

        if msg in ["no", "n", "cancel"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            _clear_prescription_upload()
            return "Okay, order cancelled."

        return "Please reply 'Yes' to confirm or 'No' to cancel."

    # Step 4: Prescription confirmation handling
    if pending_prescription_order is not None and not pending_rx_confirmation:
        if _is_no_prescription_message(msg):
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            _clear_prescription_upload()
            return (
                "Understood. I cannot place this order without a valid prescription. "
                "You can upload one later or choose a non-prescription medicine."
            )

        if msg in ["yes", "y", "upload", "done", "upload prescription"]:
            upload = pending_prescription_upload or {}
            verified = bool(upload.get("verified"))
            uploaded_for = str(upload.get("medicine_name_matched") or upload.get("medicine_name_requested") or "").strip().lower()
            pending_med = str(pending_prescription_order.get("medicine_name", "")).strip().lower()

            if not verified:
                reason = str(upload.get("verification_reason") or "Medicine name did not match prescription.")
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                _clear_prescription_upload()
                return f"Prescription invalid. Order rejected.\nReason: {reason}"

            names_mismatch = (
                uploaded_for
                and pending_med
                and uploaded_for != pending_med
                and uploaded_for not in pending_med
                and pending_med not in uploaded_for
            )
            if names_mismatch:
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                _clear_prescription_upload()
                return "Prescription invalid. Order rejected.\nReason: Medicine name does not match prescription."

            requested_qty = int(pending_prescription_order.get("quantity", pending_final_quantity or 0))
            final_qty = int(pending_final_quantity or requested_qty)

            current_order = dict(pending_prescription_order)
            current_order["quantity"] = final_qty
            latest_decision = safety_check(current_order)
            _trace_agent(
                trace,
                "Safety Agent",
                input_payload=current_order,
                output_payload=dict(latest_decision),
                status="ok" if latest_decision.get("status") != "Rejected" else "error",
            )

            if latest_decision["status"] == "Rejected":
                reason = str(latest_decision.get("reason", "Order rejected"))
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                _clear_prescription_upload()
                if "out of stock" in reason.lower():
                    _trace_agent(
                        trace,
                        "Procurement Agent",
                        input_payload={
                            "medicine_name": current_order.get("medicine_name"),
                            "reason": reason,
                        },
                        output_payload={"action": "Create refill task"},
                    )
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
                confirmation = _execute_order_with_agent_traces(
                    order,
                    trace=trace,
                    stock_before=int(latest_decision.get("stock", 0) or 0),
                    user_id=user_id,
                    phone=phone,
                )
                pending_prescription_order = None
                pending_final_quantity = None
                pending_rx_confirmation = False
                pending_partial_after_rx = False
                _clear_prescription_upload()
                return (
                    f"Only {order['quantity']} units are available (you requested {requested_qty}).\n"
                    f"{confirmation}"
                )

            order["quantity"] = final_qty
            confirmation = _execute_order_with_agent_traces(
                order,
                trace=trace,
                stock_before=int(latest_decision.get("stock", 0) or 0),
                user_id=user_id,
                phone=phone,
            )
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            _clear_prescription_upload()
            return (
                "Prescription verified.\n"
                f"{confirmation}"
            )

        if msg in ["no", "n", "cancel"]:
            pending_prescription_order = None
            pending_final_quantity = None
            pending_rx_confirmation = False
            pending_partial_after_rx = False
            _clear_prescription_upload()
            return "Okay, order cancelled because prescription is required."

        # If user sends a different query/order text, treat it as a fresh intent
        # instead of forcing the old pending-prescription flow.
        pending_prescription_order = None
        pending_final_quantity = None
        pending_rx_confirmation = False
        pending_partial_after_rx = False
        _clear_prescription_upload()

        # Continue to normal handling below for this new message.

    # Step 5: Info mode (no order intent)
    if selected_order is None and not _is_order_intent(user_message):
        normalized_message = str(user_message or "").strip()

        if not normalized_message:
            reply = _friendly_chat_reply(normalized_message)
            if reply:
                _trace_agent(
                    trace,
                    "Conversation Agent",
                    input_payload={"user_message": user_message},
                    output_payload={"reply": reply},
                )
                return reply
            return "I am here with you. Ask me anything about medicines, refills, or your health concerns."

        lookup = None
        should_try_lookup = (
            _is_medicine_lookup_intent(normalized_message)
            or len(re.findall(r"[a-zA-Z]+", normalized_message)) <= 4
        )
        if should_try_lookup:
            lookup_query = _extract_medicine_query(normalized_message)
            lookup = search_medicine(lookup_query)
            if lookup.get("status") != "Found":
                # Fallback: if sentence lookup still fails, attempt order extraction and lookup by medicine name.
                extracted = extract_order(normalized_message)
                med_name = extracted.get("medicine_name") if isinstance(extracted, dict) else None
                if med_name:
                    lookup = search_medicine(med_name)
                if lookup.get("status") == "Found":
                    _trace_agent(
                        trace,
                        "Inventory Agent",
                        input_payload={"query": lookup_query},
                        output_payload={"status": "Found"},
                    )

        if lookup and lookup.get("status") == "Found":
            rows = lookup.get("results", [])
            first_name = str(rows[0].get("medicine_name", "")).strip() if rows else ""
            if first_name:
                context["last_medicine_name"] = first_name
            lines = []
            for row in rows:
                name = row.get("medicine_name", "Unknown")
                stock = row.get("stock", "NA")
                rx = row.get("prescription_required", "NA")
                lines.append(f"- {name} | Stock: {stock} | Prescription: {rx}")
            return "Medicine Info:\n" + "\n".join(lines)

        reply = _friendly_chat_reply(normalized_message)
        if reply:
            _trace_agent(
                trace,
                "Conversation Agent",
                input_payload={"user_message": user_message},
                output_payload={"reply": reply},
            )
            return reply

        return "I can help with medicine information, symptoms, safe usage, and refills. Tell me what you need."

    # Step 6: Extract order (LLM)
    if selected_order is None:
        if context.get("last_medicine_name") and _looks_like_followup_quantity_message(user_message):
            parsed = _extract_quantity_and_unit_from_message(
                user_message,
                fallback_unit=str(context.get("last_unit") or "strip"),
            )
            if parsed["quantity"] is not None and parsed["quantity"] > 0:
                order = {
                    "medicine_name": str(context.get("last_medicine_name")),
                    "quantity": int(parsed["quantity"]),
                    "unit": str(parsed["unit"]),
                }
                _trace_agent(
                    trace,
                    "Intent Agent",
                    input_payload={"user_message": user_message, "context_used": True},
                    output_payload=dict(order),
                )
            else:
                order = extract_order(user_message)
        else:
            order = extract_order(user_message)
        if "error" not in order:
            context["last_medicine_name"] = str(order.get("medicine_name", "")).strip()
            context["last_unit"] = str(order.get("unit") or context.get("last_unit") or "strip")
            _trace_agent(
                trace,
                "Intent Agent",
                input_payload={"user_message": user_message},
                output_payload={
                    "medicine_name": order.get("medicine_name"),
                    "quantity": order.get("quantity"),
                    "unit": order.get("unit"),
                },
            )

        if "error" in order:
            err = order.get("error")
            raw = order.get("raw_output")

            can_use_context_medicine = bool(context.get("last_medicine_name"))
            missing_medicine_err = "medicine_name" in str(err or "").lower()
            if can_use_context_medicine and missing_medicine_err:
                parsed = _extract_quantity_and_unit_from_message(
                    user_message,
                    fallback_unit=str(context.get("last_unit") or "strip"),
                )
                if parsed["quantity"] is not None and parsed["quantity"] > 0:
                    order = {
                        "medicine_name": str(context.get("last_medicine_name")),
                        "quantity": int(parsed["quantity"]),
                        "unit": str(parsed["unit"]),
                    }
                    _trace_agent(
                        trace,
                        "Intent Agent",
                        input_payload={"user_message": user_message, "context_used": True},
                        output_payload=dict(order),
                    )
                else:
                    return (
                        f"I understood you mean {context.get('last_medicine_name')}, "
                        "but I still need quantity (for example: 4 tablets)."
                    )

            if "error" in order:
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
            context["last_medicine_name"] = matches
            context["last_unit"] = str(order.get("unit") or context.get("last_unit") or "strip")
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
    _trace_agent(
        trace,
        "Safety Agent",
        input_payload=dict(order),
        output_payload=dict(decision),
        status="ok" if decision.get("status") != "Rejected" else "error",
    )

    if decision["status"] == "Rejected":
        reason = str(decision.get("reason", "Order rejected"))
        if "out of stock" in reason.lower():
            _trace_agent(
                trace,
                "Procurement Agent",
                input_payload={
                    "medicine_name": order.get("medicine_name"),
                    "reason": reason,
                },
                output_payload={"action": "Create refill task"},
            )
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
            _clear_prescription_upload()
            return _prescription_required_response(
                "Prescription Required.\n"
                "Please click 'Add Prescription' and upload a clear photo to continue."
            )

        confirmation = _execute_order_with_agent_traces(
            order,
            trace=trace,
            stock_before=int(stock),
            user_id=user_id,
            phone=phone,
        )
        return f"Stock available.\n{confirmation}"
