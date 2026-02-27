// Select elements (may not exist on every page)
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.querySelector("#new-chat-btn");
const input = document.querySelector("#chat-input");
const chat = document.querySelector(".chat");

const BACKEND_URL = "http://127.0.0.1:8000/chat";
const INVENTORY_URL = "http://127.0.0.1:8000/inventory";
const CHAT_STORAGE_KEY = "pharma_chat_messages";
const ORDERS_STORAGE_KEY = "pharma_orders";

const WELCOME_MESSAGE =
  "Welcome to the Medico AI Pharmacist. How may I assist you with your medication or health-related queries today?";

const LEGACY_ANALYZING_MESSAGE =
  "Analyzing medicine, dosage, stock availability, and prescription rules...";
let typingIndicatorEl = null;

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

function showTypingIndicator() {
  if (!chat || typingIndicatorEl) return;
  const msg = document.createElement("div");
  msg.className = "bubble ai typing-indicator";
  msg.innerHTML = `
    <span class="ai-logo" title="AI">🤖</span>
    <span class="typing-dots" aria-label="AI is typing">
      <span></span><span></span><span></span>
    </span>
  `;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
  typingIndicatorEl = msg;
}

function hideTypingIndicator() {
  if (!typingIndicatorEl) return;
  typingIndicatorEl.remove();
  typingIndicatorEl = null;
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
  // Save only class (ai/user) and text (strip logo for ai)
  const messages = Array.from(chat.querySelectorAll('.bubble'))
    .filter((el) => !el.classList.contains("typing-indicator"))
    .map((el) => {
    let className = el.classList.contains('ai') ? 'ai' : 'user';
    let text = className === 'ai'
      ? el.querySelector('.ai-text')?.innerText || ''
      : el.querySelector('.user-text')?.innerText || '';
    return { className, text };
  });
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
      if (!item || (item.className !== "ai" && item.className !== "user")) return;
      appendMessage(item.className, item.text || "");
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

// Clear chat history on login if needed
if (window.location.pathname.endsWith('chat.html')) {
  const loggedIn = localStorage.getItem('pharma_logged_in');
  if (loggedIn === 'true' && localStorage.getItem('pharma_clear_chat') === 'true') {
    localStorage.removeItem(CHAT_STORAGE_KEY);
    localStorage.setItem('pharma_clear_chat', 'false');
  }
}
restoreChat();

async function getInventoryPriceMap() {
  try {
    const res = await fetch(INVENTORY_URL);
    if (!res.ok) return {};
    const rows = await res.json();
    if (!Array.isArray(rows)) return {};

    return rows.reduce((acc, row) => {
      const name = String(row.medicine_name || "").trim().toLowerCase();
      const price = Number(row.price);
      if (name && Number.isFinite(price)) acc[name] = price;
      return acc;
    }, {});
  } catch {
    return {};
  }
}

function extractConfirmedOrder(replyText) {
  const text = String(replyText || "");
  if (!/order confirmed/i.test(text)) return null;

  const medicineMatch = text.match(/Medicine:\s*(.+)/i);
  const quantityMatch = text.match(/Quantity Ordered:\s*(\d+)/i);
  const unitPriceMatch = text.match(/Unit Price:\s*EUR\s*([0-9]+(?:\.[0-9]+)?)/i);
  const totalPriceMatch = text.match(/Total Price:\s*EUR\s*([0-9]+(?:\.[0-9]+)?)/i);
  if (!medicineMatch || !quantityMatch) return null;

  return {
    medicine_name: medicineMatch[1].trim(),
    quantity: Number(quantityMatch[1]),
    unit_price: unitPriceMatch ? Number(unitPriceMatch[1]) : NaN,
    total_price: totalPriceMatch ? Number(totalPriceMatch[1]) : NaN,
  };
}

async function trackPlacedOrderFromReply(replyText) {
  const parsed = extractConfirmedOrder(replyText);
  if (!parsed) return;

  const username = localStorage.getItem("pharma_username") || "User";
  const priceMap = await getInventoryPriceMap();
  let unitPrice = Number(parsed.unit_price);
  if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
    unitPrice = Number(priceMap[parsed.medicine_name.toLowerCase()] || 0);
  }
  let totalPrice = Number(parsed.total_price);
  if (!Number.isFinite(totalPrice) || totalPrice <= 0) {
    totalPrice = unitPrice * parsed.quantity;
  }

  const orders = JSON.parse(localStorage.getItem(ORDERS_STORAGE_KEY) || "[]");
  const newOrder = {
    username,
    medicine_name: parsed.medicine_name,
    quantity: parsed.quantity,
    unit_price: unitPrice,
    total_price: totalPrice,
    ordered_at: new Date().toISOString(),
  };

  orders.push(newOrder);
  localStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(orders));
}

async function sendMessage(textFromVoice) {
  const message = textFromVoice || input.value.trim();
  if (!message) return;

  appendMessage("user", message);

  if (input) input.value = "";
  if (sendBtn) sendBtn.disabled = true;
  showTypingIndicator();

  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      hideTypingIndicator();
      appendMessage(
        "ai",
        `Backend error: ${res.status} ${res.statusText}`
      );
      return;
    }

    const data = await res.json();
    hideTypingIndicator();
    const replyText = data.reply || "No reply received from backend.";
    appendMessage("ai", replyText);
    await trackPlacedOrderFromReply(replyText);
  } catch (err) {
    hideTypingIndicator();
    appendMessage(
      "ai",
      "Cannot connect to backend. Start backend on http://127.0.0.1:8000."
    );
    console.error(err);
  } finally {
    hideTypingIndicator();
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
