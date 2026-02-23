// Select elements
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.querySelector("#new-chat-btn");
const input = document.querySelector("#chat-input");
const chat = document.querySelector(".chat");
const BACKEND_URL = "http://127.0.0.1:8000/chat";
const CHAT_STORAGE_KEY = "pharma_chat_messages";
const WELCOME_MESSAGE = "Hello! I’m your AI Pharmacist. How can I help today?";

// Send message on button click
sendBtn.addEventListener("click", sendMessage);
newChatBtn.addEventListener("click", startNewChat);

// Send message on Enter key
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

function appendMessage(className, text) {
  const msg = document.createElement("div");
  msg.className = className;
  msg.innerText = text;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
  persistChat();
}

function persistChat() {
  const messages = Array.from(chat.querySelectorAll(".ai, .user")).map((el) => ({
    className: el.className,
    text: el.innerText,
  }));
  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
}

function restoreChat() {
  const raw = localStorage.getItem(CHAT_STORAGE_KEY);
  if (!raw) return;

  try {
    const saved = JSON.parse(raw);
    if (!Array.isArray(saved) || saved.length === 0) return;

    chat.innerHTML = "";
    saved.forEach((item) => {
      if (!item || (item.className !== "ai" && item.className !== "user")) return;
      const msg = document.createElement("div");
      msg.className = item.className;
      msg.innerText = item.text || "";
      chat.appendChild(msg);
    });
    chat.scrollTop = chat.scrollHeight;
  } catch {
    // Ignore invalid storage and keep current chat UI
  }
}

function startNewChat() {
  chat.innerHTML = "";
  appendMessage("ai", WELCOME_MESSAGE);
  input.value = "";
}

restoreChat();

async function sendMessage() {
  const message = input.value.trim();
  if (message === "") return;

  appendMessage("user", message);

  input.value = "";
  sendBtn.disabled = true;

  appendMessage("ai", "Analyzing medicine, dosage, stock availability, and prescription rules...");

  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      appendMessage("ai", `Backend error: ${res.status} ${res.statusText}`);
      return;
    }

    const data = await res.json();
    appendMessage("ai", data.reply || "No reply received from backend.");
  } catch (err) {
    appendMessage("ai", "Cannot connect to backend. Start backend on http://127.0.0.1:8000.");
    console.error(err);
  } finally {
    sendBtn.disabled = false;
  }
}
