#fast API entry point

from fastapi import FastAPI
from pydantic import BaseModel

from pharmacy_agent import pharmacy_chatbot

app = FastAPI(title="Agentic AI Pharmacy System")

# Request format from frontend
class ChatRequest(BaseModel):
    message: str

# Response format back to frontend
class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def home():
    return {"status": "Pharmacy Agent Backend Running"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_message = req.message

    # Call your agent pipeline
    bot_reply = pharmacy_chatbot(user_message)

    return {"reply": bot_reply}
