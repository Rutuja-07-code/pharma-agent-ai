#fast API entry point
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


from pharmacy_agent import pharmacy_chatbot
from inventory_api import router as inventory_router

app = FastAPI(title="Agentic AI Pharmacy System")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_message = req.message

    # Call your agent pipeline
    bot_reply = pharmacy_chatbot(user_message)

    return {"reply": bot_reply}


# Serve frontend files from the same FastAPI app so only one server is needed.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
