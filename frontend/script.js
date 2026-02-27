// Select elements (may not exist on every page)
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.querySelector("#new-chat-btn");
const input = document.querySelector("#chat-input");
const chat = document.querySelector(".chat");

const BACKEND_URL = "http://127.0.0.1:8000/chat";
const CHAT_STORAGE_KEY = "pharma_chat_messages";

const WELCOME_MESSAGE =
  "Welcome to the CureOS AI Pharmacist. How may I assist you with your medication or health-related queries today?";

const LEGACY_ANALYZING_MESSAGE =
  "Analyzing medicine, dosage, stock availability, and prescription rules...";

// Attach events only if elements exist
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (newChatBtn) newChatBtn.addEventListener("click", startNewChat);

if (input) {
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
}

function appendMessage(className, text) {
  const safeText = className === "ai" ? sanitizeAiText(text) : text;
  if (!safeText || !chat) return;

  const msg = document.createElement("div");
  msg.className = className;
  msg.innerText = safeText;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
  persistChat();
}

function sanitizeAiText(text) {
  const value = String(text || "").trim();
  if (!value) return "";
  if (value === LEGACY_ANALYZING_MESSAGE) return "";

  return value
    .replace(LEGACY_ANALYZING_MESSAGE, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function persistChat() {
  if (!chat) return;

  const messages = Array.from(
    chat.querySelectorAll(".ai, .user")
  ).map((el) => ({
    className: el.className,
    text: el.innerText,
  }));

  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
}

function restoreChat() {
  if (!chat) return;

  const raw = localStorage.getItem(CHAT_STORAGE_KEY);
  if (!raw) return;

  try {
    const saved = JSON.parse(raw);
    if (!Array.isArray(saved) || saved.length === 0) return;

    chat.innerHTML = "";

    saved.forEach((item) => {
      if (!item || (item.className !== "ai" && item.className !== "user"))
        return;

      const msg = document.createElement("div");
      msg.className = item.className;
      msg.innerText =
        item.className === "ai"
          ? sanitizeAiText(item.text)
          : item.text || "";

      if (!msg.innerText) return;

      chat.appendChild(msg);
    });

    chat.scrollTop = chat.scrollHeight;
  } catch {
    // ignore broken storage
  }
}

function startNewChat() {
  if (!chat) return;
  chat.innerHTML = "";
  appendMessage("ai", WELCOME_MESSAGE);
  if (input) input.value = "";
}

restoreChat();

async function sendMessage(textFromVoice) {
  const message = textFromVoice || input.value.trim();
  if (!message) return;

  appendMessage("user", message);

  if (input) input.value = "";
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      appendMessage(
        "ai",
        `Backend error: ${res.status} ${res.statusText}`
      );
      return;
    }

    const data = await res.json();
    appendMessage("ai", data.reply || "No reply received from backend.");
  } catch (err) {
    appendMessage(
      "ai",
      "Cannot connect to backend. Start backend on http://127.0.0.1:8000."
    );
    console.error(err);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

/* VOICE COMMAND */
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";

  const micBtn = document.querySelector("#mic-btn");

  if (micBtn) {
    micBtn.addEventListener("click", () => recognition.start());
  }

  recognition.onresult = (e) => {
    const voiceText = e.results[0][0].transcript;
    sendMessage(voiceText);
  };
} else {
  const micBtn = document.querySelector("#mic-btn");
  if (micBtn) micBtn.style.display = "none";
}