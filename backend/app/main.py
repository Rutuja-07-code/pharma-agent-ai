from pathlib import Path
import logging
import os
import re
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langfuse import Langfuse
from pydantic import BaseModel


from pharmacy_agent import pharmacy_chatbot
from inventory_api import router as inventory_router
from order_executor import place_order

app = FastAPI(title="Agentic AI Pharmacy System")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
logger = logging.getLogger("pharma.langfuse")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount inventory API
app.include_router(inventory_router)

# Request format from frontend
class ChatRequest(BaseModel):
    message: str

# Response format back to frontend
class ChatResponse(BaseModel):
    reply: str
    payment_required: bool = False
    payment: Optional[Dict[str, Any]] = None


class CreatePaymentRequest(BaseModel):
    medicine_name: str
    quantity: int
    total_price: float
    currency: str = "INR"


class CreatePaymentResponse(BaseModel):
    provider: str = "upi_intent"
    amount: int
    currency: str
    name: str
    description: str
    upi_link: str = ""
    qr_url: str = ""


class ConfirmPaymentRequest(BaseModel):
    medicine_name: str
    quantity: int
    payment_mode: str = "upi_intent"
    upi_confirmed: bool = False


class ConfirmPaymentResponse(BaseModel):
    placed: bool
    reply: str


def _init_langfuse() -> Optional[Langfuse]:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = (
        os.getenv("LANGFUSE_BASE_URL")
        or os.getenv("LANGFUSE_HOST")
        or "https://cloud.langfuse.com"
    )

    if not public_key or not secret_key:
        logger.warning(
            "Langfuse disabled: LANGFUSE_PUBLIC_KEY and/or LANGFUSE_SECRET_KEY missing."
        )
        return None

    try:
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
        )
        logger.info("Langfuse enabled. base_url=%s", base_url)
        return client
    except Exception as exc:
        logger.exception("Langfuse init failed: %s", exc)
        return None


langfuse_client = _init_langfuse()


def _sanitize_reply(text: str) -> str:
    phrase = r"Analyzing medicine, dosage, stock availability, and prescription rules\.\.\.|Analyzing medicine, dosage, stock availability, and prescription rules…"
    cleaned = re.sub(phrase, "", str(text or ""), flags=re.IGNORECASE)
    return cleaned.strip()


def _resolve_chat_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and result.get("type") == "payment_required":
        return {
            "reply": _sanitize_reply(result.get("message", "Payment required to place order.")),
            "payment_required": True,
            "payment": result.get("payment"),
        }

    return {
        "reply": _sanitize_reply(result),
        "payment_required": False,
        "payment": None,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    global langfuse_client
    user_message = req.message

    if langfuse_client is None:
        langfuse_client = _init_langfuse()

    if langfuse_client is None:
        result = _resolve_chat_result(pharmacy_chatbot(user_message))
        return result

    try:
        with langfuse_client.start_as_current_span(
            name="pharma-chat-request",
            input={"message": user_message},
            metadata={"route": "/chat"},
        ):
            result = _resolve_chat_result(pharmacy_chatbot(user_message))
            langfuse_client.update_current_span(
                output={
                    "reply": result["reply"],
                    "payment_required": result["payment_required"],
                }
            )
            return result
    except Exception as exc:
        try:
            langfuse_client.update_current_span(
                level="ERROR",
                status_message=f"/chat failed: {exc}",
            )
        except Exception:
            pass
        raise
    finally:
        langfuse_client.flush()


@app.post("/payment/create", response_model=CreatePaymentResponse)
def create_payment(req: CreatePaymentRequest):
    amount = max(1, int(round(float(req.total_price) * 100)))
    currency = "INR"
    name = "Medico Pharmacy"
    description = f"Order for {req.medicine_name} x {req.quantity}"

    # UPI intent mode only (personal UPI ID).
    personal_upi_id = os.getenv("UPI_ID", "").strip()
    if not personal_upi_id:
        raise HTTPException(
            status_code=500,
            detail="UPI_ID is not configured. Set UPI_ID (example: yourname@oksbi).",
        )

    payee_name = os.getenv("UPI_PAYEE_NAME", "Medico Pharmacy")
    txn_note = f"Medicine order {req.medicine_name}"
    txn_ref = f"MED{abs(hash((req.medicine_name, req.quantity, amount))) % 1000000000}"
    upi_link = (
        "upi://pay"
        f"?pa={personal_upi_id}"
        f"&pn={payee_name}"
        f"&am={amount/100:.2f}"
        f"&cu=INR"
        f"&tn={txn_note}"
        f"&tr={txn_ref}"
    )
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=260x260&data={upi_link}"
    )

    return {
        "provider": "upi_intent",
        "amount": amount,
        "currency": currency,
        "name": name,
        "description": description,
        "upi_link": upi_link,
        "qr_url": qr_url,
    }


@app.post("/payment/confirm", response_model=ConfirmPaymentResponse)
def confirm_payment(req: ConfirmPaymentRequest):
    if req.payment_mode != "upi_intent":
        raise HTTPException(status_code=400, detail="Unsupported payment mode.")
    if not req.upi_confirmed:
        raise HTTPException(status_code=400, detail="UPI payment not confirmed.")

    confirmation = place_order(
        {"medicine_name": req.medicine_name, "quantity": int(req.quantity)}
    )
    placed = "Order Confirmed!" in str(confirmation)
    return {"placed": placed, "reply": _sanitize_reply(confirmation)}


# Serve frontend files from the same FastAPI app so only one server is needed.
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
