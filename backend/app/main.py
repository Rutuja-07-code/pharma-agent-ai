from pathlib import Path
import logging
import os
import re
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langfuse import Langfuse
from pydantic import BaseModel


from pharmacy_agent import (
    pharmacy_chatbot,
    get_pending_prescription_context,
    set_prescription_upload_verification,
)
from inventory_api import router as inventory_router
from prescription_store import save_and_verify_prescription

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
    prescription_required: bool = False


class PrescriptionSubmitRequest(BaseModel):
    image_data: str
    filename: Optional[str] = None


class PrescriptionSubmitResponse(BaseModel):
    accepted: bool
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
    if isinstance(result, dict) and result.get("type") == "prescription_required":
        return {
            "reply": _sanitize_reply(result.get("message", "Prescription is required to place this order.")),
            "prescription_required": True,
        }

    return {
        "reply": _sanitize_reply(result),
        "prescription_required": False,
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

    result = _resolve_chat_result(pharmacy_chatbot("upload prescription"))
    return {"accepted": bool(record.get("verified")), "reply": result["reply"]}


# Serve frontend files from the same FastAPI app so only one server is needed.
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

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
