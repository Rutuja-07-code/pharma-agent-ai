from pathlib import Path
import logging
import os
import re
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langfuse import Langfuse
from pydantic import BaseModel

from pharmacy_agent import pharmacy_chatbot

app = FastAPI(title="Agentic AI Pharmacy System")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
logger = logging.getLogger("pharma.langfuse")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request format from frontend
class ChatRequest(BaseModel):
    message: str

# Response format back to frontend
class ChatResponse(BaseModel):
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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    global langfuse_client
    user_message = req.message

    if langfuse_client is None:
        langfuse_client = _init_langfuse()

    if langfuse_client is None:
        bot_reply = pharmacy_chatbot(user_message)
        bot_reply = _sanitize_reply(bot_reply)
        return {"reply": bot_reply}

    try:
        with langfuse_client.start_as_current_span(
            name="pharma-chat-request",
            input={"message": user_message},
            metadata={"route": "/chat"},
        ):
            bot_reply = pharmacy_chatbot(user_message)
            bot_reply = _sanitize_reply(bot_reply)
            langfuse_client.update_current_span(output={"reply": bot_reply})
            return {"reply": bot_reply}
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


# Serve frontend files from the same FastAPI app so only one server is needed.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
