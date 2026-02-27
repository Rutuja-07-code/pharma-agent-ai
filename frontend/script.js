// Select elements (may not exist on every page)
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.querySelector("#new-chat-btn");
const input = document.querySelector("#chat-input");
let chat = document.querySelector(".chat");
const BACKEND_URL = "http://127.0.0.1:8000/chat";
const CHAT_STORAGE_KEY = "pharma_chat_messages";
const WELCOME_MESSAGE = "Welcome to the CureOS AI Pharmacist. How may I assist you with your medication or health‑related queries today?";

// attach events only if elements are present
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (newChatBtn) newChatBtn.addEventListener("click", startNewChat);

// Send message on Enter key
if (input) {
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
}

// Send message on Enter key
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

function appendMessage(className, text) {
  if (!chat) chat = document.querySelector(".chat");
  if (!chat) return;
  const msg = document.createElement("div");
  msg.className = `bubble ${className}`;
  if (className === "ai") {
    // Add AI logo (robot emoji or SVG)
    msg.innerHTML = `<span class="ai-logo" title="AI">🤖</span><span class="ai-text">${text.replace(/\n/g, '<br>')}</span>`;
  } else {
    msg.innerHTML = `<span class="user-text">${text.replace(/\n/g, '<br>')}</span>`;
  }
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
  persistChat();
}

function persistChat() {
  // Save only class (ai/user) and text (strip logo for ai)
  const messages = Array.from(chat.querySelectorAll('.bubble')).map((el) => {
    let className = el.classList.contains('ai') ? 'ai' : 'user';
    let text = className === 'ai'
      ? el.querySelector('.ai-text')?.innerText || ''
      : el.querySelector('.user-text')?.innerText || '';
    return { className, text };
  });
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
      appendMessage(item.className, item.text || "");
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

// Clear chat history on login if needed
if (window.location.pathname.endsWith('chat.html')) {
  const loggedIn = localStorage.getItem('pharma_logged_in');
  if (loggedIn === 'true' && localStorage.getItem('pharma_clear_chat') === 'true') {
    localStorage.removeItem(CHAT_STORAGE_KEY);
    localStorage.setItem('pharma_clear_chat', 'false');
  }
}
restoreChat();

// if page lacks chat but has input, still set focus on input
if (!chat && input) input.focus();

async function sendMessage(textFromVoice) {
  const message = textFromVoice || input.value.trim();
  if (message === "") return;

  appendMessage("user", message);

  input.value = "";
  sendBtn.disabled = true;

  appendMessage("ai", "Please wait while I process your request…");

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
