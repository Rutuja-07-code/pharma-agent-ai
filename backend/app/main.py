from pathlib import Path
import logging
import os
import re
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langfuse import Langfuse
from pydantic import BaseModel

try:
    from backend.app.pharmacy_agent import (
        pharmacy_chatbot,
        get_pending_prescription_context,
        set_prescription_upload_verification,
    )
except ModuleNotFoundError:
    from pharmacy_agent import (
        pharmacy_chatbot,
        get_pending_prescription_context,
        set_prescription_upload_verification,
    )

try:
    from backend.app.inventory_api import router as inventory_router
except ModuleNotFoundError:
    from inventory_api import router as inventory_router

try:
    from backend.app.prescription_store import save_and_verify_prescription
except ModuleNotFoundError:
    from prescription_store import save_and_verify_prescription

try:
    from backend.app.admin_reminder_service import preview_admin_reminders, send_admin_reminders
except ModuleNotFoundError:
    from admin_reminder_service import preview_admin_reminders, send_admin_reminders

try:
    from backend.app.refill_engine import get_due_refills
except ModuleNotFoundError:
    from refill_engine import get_due_refills

try:
    from backend.app.whatsapp_service import run_daily_whatsapp_reminders
except ModuleNotFoundError:
    from whatsapp_service import run_daily_whatsapp_reminders

try:
    from backend.app.history_data_loader import load_orders
except ModuleNotFoundError:
    from history_data_loader import load_orders

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:
    BackgroundScheduler = None


app = FastAPI(title="Agentic AI Pharmacy System")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
REPO_DIR = Path(__file__).resolve().parents[2]
logger = logging.getLogger("pharma.langfuse")

REFILL_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "Consumer Order History 1.xlsx"
CONTACT_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "patient_contacts.csv"
ORDER_HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "Consumer Order History 1.xlsx"
scheduler = None


def _load_env_file() -> None:
    env_path = REPO_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        if key:
            os.environ.setdefault(key, value)


_load_env_file()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount inventory API
app.include_router(inventory_router)


class UserRegisterRequest(BaseModel):
    username: str
    phone: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    phone: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    prescription_required: bool = False


class PrescriptionSubmitRequest(BaseModel):
    image_data: str
    filename: Optional[str] = None


class PrescriptionSubmitResponse(BaseModel):
    accepted: bool
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
    phrase = r"Analyzing medicine, dosage, stock availability, and prescription rules\.\.\.|Analyzing medicine, dosage, stock availability, and prescription rules\?+"
    cleaned = re.sub(phrase, "", str(text or ""), flags=re.IGNORECASE)
    return cleaned.strip()


def _resolve_chat_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and result.get("type") == "prescription_required":
        return {
            "reply": _sanitize_reply(result.get("message", "Prescription is required to place this order.")),
            "prescription_required": True,
        }

    return {
        "reply": _sanitize_reply(result),
        "prescription_required": False,
    }


def _build_agent_tracer(client: Optional[Langfuse]):
    if client is None:
        return None

    def _trace_agent_step(
        agent_name: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        status: str,
    ) -> None:
        try:
            with client.start_as_current_span(
                name=agent_name,
                input=input_payload or {},
                metadata={
                    "component": "pharmacy-agent",
                    "status": status,
                },
            ):
                client.update_current_span(output=output_payload or {})
        except Exception as exc:
            logger.exception("Langfuse agent-step trace failed for %s: %s", agent_name, exc)

    return _trace_agent_step


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    global langfuse_client
    user_message = req.message
    user_id = req.user_id or "GUEST"
    phone = req.phone
    
    logger.info(f"Chat request - user_id: {user_id}, phone: {phone}")

    if langfuse_client is None:
        langfuse_client = _init_langfuse()

    if langfuse_client is None:
        result = _resolve_chat_result(pharmacy_chatbot(user_message, user_id=user_id, phone=phone))
        return result

    try:
        with langfuse_client.start_as_current_span(
            name="pharma-chat-request",
            input={"message": user_message, "user_id": user_id},
            metadata={"route": "/chat"},
        ):
            tracer = _build_agent_tracer(langfuse_client)
            result = _resolve_chat_result(pharmacy_chatbot(user_message, trace=tracer, user_id=user_id, phone=phone))
            langfuse_client.update_current_span(
                output={
                    "reply": result["reply"],
                    "prescription_required": result["prescription_required"],
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


@app.post("/prescription/submit", response_model=PrescriptionSubmitResponse)
def submit_prescription(req: PrescriptionSubmitRequest):
    context = get_pending_prescription_context()
    if not context or not context.get("medicine_name"):
        raise HTTPException(
            status_code=400,
            detail="No prescription-required order is pending right now.",
        )

    try:
        record = save_and_verify_prescription(
            image_data=req.image_data,
            medicine_name=context["medicine_name"],
            filename=req.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    set_prescription_upload_verification(record)

    tracer = _build_agent_tracer(langfuse_client)
    result = _resolve_chat_result(pharmacy_chatbot("upload prescription", trace=tracer))
    return {"accepted": bool(record.get("verified")), "reply": result["reply"]}


@app.post("/upload-prescription/")
async def upload_prescription(image: UploadFile = File(...)):
    # Lazy import so server can still start even if OCR deps are not installed.
    try:
        from orc.orc_service import extract_text_from_image
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OCR service unavailable: {exc}",
        )

    file_bytes = await image.read()
    extracted_text = extract_text_from_image(file_bytes)
    return {"extracted_text": extracted_text}


def _int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


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


@app.get("/admin/sales-overview")
def get_sales_overview():
    try:
        df = load_orders(str(ORDER_HISTORY_PATH))
        df['date'] = df['purchase_date'].dt.date
        
        sales_by_date = df.groupby('date').agg(
            orders=('patient_id', 'nunique'),
            revenue=('total_price_(eur)', 'sum'),
            items=('quantity', 'sum')
        ).reset_index()
        
        sales_by_date['avgOrder'] = (sales_by_date['revenue'] / sales_by_date['orders']).round(2)
        sales_by_date['date'] = sales_by_date['date'].astype(str)
        
        return sales_by_date.tail(10).to_dict(orient='records')
    except Exception as e:
        logger.exception(f"Failed to load sales overview: {e}")
        return []


@app.get("/admin/top-products")
def get_top_products():
    try:
        df = load_orders(str(ORDER_HISTORY_PATH))
        
        product_sales = df.groupby('product_name').agg(
            units=('quantity', 'sum'),
            revenue=('total_price_(eur)', 'sum')
        ).reset_index()
        
        product_sales = product_sales.sort_values('revenue', ascending=False).head(10)
        product_sales['rank'] = range(1, len(product_sales) + 1)
        
        return product_sales[['rank', 'product_name', 'units', 'revenue']].to_dict(orient='records')
    except Exception as e:
        logger.exception(f"Failed to load top products: {e}")
        return []


@app.get("/admin/user-orders")
def get_user_orders():
    try:
        import pandas as pd
        orders_df = load_orders(str(ORDER_HISTORY_PATH))
        orders_df['patient_id'] = orders_df['patient_id'].astype(str).str.strip()
        
        try:
            contacts_df = pd.read_csv(str(CONTACT_FILE_PATH))
            contacts_df['patient_id'] = contacts_df['patient_id'].astype(str).str.strip()
            contacts_df['phone'] = contacts_df['phone'].astype(str)
            
            merged = orders_df.merge(
                contacts_df[['patient_id', 'phone']],
                on='patient_id',
                how='left'
            )
        except Exception as e:
            logger.exception(f"Failed to merge contacts: {e}")
            merged = orders_df.copy()
            merged['phone'] = None
        
        result = merged[['patient_id', 'product_name', 'purchase_date', 'quantity']].copy()
        
        if 'phone' in merged.columns:
            result['phone'] = merged['phone']
        else:
            result['phone'] = None
        
        result['purchase_date'] = result['purchase_date'].dt.strftime('%Y-%m-%d %H:%M')
        result = result.sort_values('purchase_date', ascending=False)
        
        result = result[['patient_id', 'phone', 'product_name', 'purchase_date', 'quantity']]
        
        return result.to_dict(orient='records')
    except Exception as e:
        logger.exception(f"Failed to load user orders: {e}")
        return []


@app.post("/auth/register")
def register_user(req: UserRegisterRequest):
    try:
        import pandas as pd
        
        # Check if user already exists
        if CONTACT_FILE_PATH.exists():
            contacts_df = pd.read_csv(CONTACT_FILE_PATH)
            if req.username in contacts_df['patient_id'].values:
                raise HTTPException(status_code=400, detail="Username already exists")
        else:
            contacts_df = pd.DataFrame(columns=['patient_id', 'email', 'phone', 'whatsapp', 'last_purchase_date', 'days_supply'])
        
        # Add new user
        new_user = {
            'patient_id': req.username,
            'email': f"{req.username.lower()}@example.com",
            'phone': req.phone,
            'whatsapp': req.phone,
            'last_purchase_date': None,
            'days_supply': 30
        }
        
        contacts_df = pd.concat([contacts_df, pd.DataFrame([new_user])], ignore_index=True)
        contacts_df.to_csv(CONTACT_FILE_PATH, index=False)
        
        return {"success": True, "message": "User registered successfully"}
    except Exception as e:
        logger.exception(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/login")
def login_user(req: UserLoginRequest):
    try:
        import pandas as pd
        
        if not CONTACT_FILE_PATH.exists():
            raise HTTPException(status_code=400, detail="No users registered")
        
        contacts_df = pd.read_csv(CONTACT_FILE_PATH)
        user_row = contacts_df[contacts_df['patient_id'] == req.username]
        
        if user_row.empty:
            raise HTTPException(status_code=400, detail="User not found")
        
        user_data = user_row.iloc[0]
        return {
            "success": True,
            "user": {
                "username": user_data['patient_id'],
                "phone": str(user_data['phone'])
            }
        }
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/whatsapp")
async def whatsapp_inbound_webhook(request: Request):
    """
    Twilio WhatsApp inbound webhook endpoint.
    Configure this URL in Twilio Sandbox to override default auto-replies.
    """
    try:
        from twilio.twiml.messaging_response import MessagingResponse
    except Exception:
        return Response(
            content="<Response><Message>Server misconfigured: twilio package missing.</Message></Response>",
            media_type="application/xml",
        )

    form = await request.form()
    incoming_text = str(form.get("Body", "")).strip().lower()

    twiml = MessagingResponse()
    if incoming_text == "yes":
        twiml.message(
            "Thanks. Your refill request is confirmed. Our team will process your order shortly."
        )
    else:
        twiml.message("Reply YES to confirm your refill request.")

    return Response(content=str(twiml), media_type="application/xml")


def _run_due_refill_job():
    due_df = get_due_refills(str(REFILL_FILE_PATH))
    logger.info("Due refill scheduler job completed. rows=%s", len(due_df))

    whatsapp_enabled = os.getenv("WHATSAPP_REMINDER_ENABLED", "false").lower() == "true"
    if whatsapp_enabled:
        try:
            summary = run_daily_whatsapp_reminders()
            logger.info("WhatsApp reminder job completed: %s", summary)
        except Exception as exc:
            logger.exception("WhatsApp reminder job failed: %s", exc)


@app.on_event("startup")
def start_scheduler():
    global scheduler
    if BackgroundScheduler is None:
        logger.warning("APScheduler not installed. Skipping due-refill scheduler startup.")
        return
    if scheduler is None:
        hour = _int_env("REMINDER_SCHEDULE_HOUR", 9, 0, 23)
        minute = _int_env("REMINDER_SCHEDULE_MINUTE", 0, 0, 59)
        run_on_startup = os.getenv("REMINDER_RUN_ON_STARTUP", "false").lower() == "true"

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            _run_due_refill_job,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="due_refill_job",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        logger.info("Due-refill scheduler started (daily at %02d:%02d).", hour, minute)
        if run_on_startup:
            _run_due_refill_job()


@app.on_event("shutdown")
def stop_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Due-refill scheduler stopped.")


# Serve frontend files from the same FastAPI app so only one server is needed.
# Keep this at the end so API routes like /admin/* are matched first.
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
