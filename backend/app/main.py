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

try:
    from backend.app.pharmacy_agent import pharmacy_chatbot
except ModuleNotFoundError:
    from pharmacy_agent import pharmacy_chatbot

try:
    from backend.app.inventory_api import router as inventory_router
except ModuleNotFoundError:
    from inventory_api import router as inventory_router

try:
    from backend.app.order_executor import place_order
except ModuleNotFoundError:
    from order_executor import place_order

try:
    from backend.app.admin_reminder_service import preview_admin_reminders, send_admin_reminders
except ModuleNotFoundError:
    from admin_reminder_service import preview_admin_reminders, send_admin_reminders

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


class AdminReminderRequest(BaseModel):
    admin_name: str
    admin_contact: str
    max_overdue_days: int = 9999
    dry_run: bool = True


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

try:
    from backend.app.refill_engine import get_due_refills
except ModuleNotFoundError:
    from refill_engine import get_due_refills

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:
    BackgroundScheduler = None

REFILL_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "Consumer Order History 1.xlsx"
CONTACT_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "patient_contacts.csv"
scheduler = None


@app.get("/admin/due-refills")
def show_due_refills():
    due_df = get_due_refills(str(REFILL_FILE_PATH))

    return due_df[[
        "patient_id",
        "product_name",
        "next_refill_date"
    ]].to_dict(orient="records")


@app.get("/admin/reminders/preview")
def admin_preview_reminders(max_overdue_days: int = 9999):
    return preview_admin_reminders(
        history_file=str(REFILL_FILE_PATH),
        contact_file=str(CONTACT_FILE_PATH),
        max_overdue_days=max_overdue_days,
    )


@app.post("/admin/reminders/send")
def admin_send_reminders(req: AdminReminderRequest):
    return send_admin_reminders(
        history_file=str(REFILL_FILE_PATH),
        contact_file=str(CONTACT_FILE_PATH),
        admin_name=req.admin_name,
        admin_contact=req.admin_contact,
        max_overdue_days=req.max_overdue_days,
        dry_run=req.dry_run,
    )


def _run_due_refill_job():
    due_df = get_due_refills(str(REFILL_FILE_PATH))
    logger.info("Due refill scheduler job completed. rows=%s", len(due_df))


@app.on_event("startup")
def start_scheduler():
    global scheduler
    if BackgroundScheduler is None:
        logger.warning("APScheduler not installed. Skipping due-refill scheduler startup.")
        return
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(_run_due_refill_job, "interval", hours=24, id="due_refill_job", replace_existing=True)
        scheduler.start()
        logger.info("Due-refill scheduler started (every 24 hours).")


@app.on_event("shutdown")
def stop_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Due-refill scheduler stopped.")
