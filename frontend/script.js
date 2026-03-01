// Select elements (may not exist on every page)
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.querySelector("#new-chat-btn");
const input = document.querySelector("#chat-input");
const chat = document.querySelector(".chat");
const chatHistoryList = document.querySelector("#chat-history-list");
const submitPrescriptionBtn = document.querySelector("#submit-prescription-btn");
const prescriptionPhotoInput = document.querySelector("#prescription-photo-input");

function normalizeBaseUrl(url) {
  return String(url || "").replace(/\/+$/, "");
}

function getBackendCandidates() {
  const explicit = normalizeBaseUrl(
    localStorage.getItem("PHARMA_API_BASE") || window.PHARMA_API_BASE
  );
  const candidates = [];

  if (explicit) candidates.push(explicit);
  if (!explicit) candidates.push("http://127.0.0.1:8000");

  if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
    const sameOrigin = normalizeBaseUrl(window.location.origin);
    if (sameOrigin) candidates.push(sameOrigin);
  }

  ["8000", "8001", "8002", "8003"].forEach((port) => {
    candidates.push(`http://127.0.0.1:${port}`);
    candidates.push(`http://localhost:${port}`);
  });

  return [...new Set(candidates)];
}

const BACKEND_BASE_CANDIDATES = getBackendCandidates();
let ACTIVE_BACKEND_BASE = BACKEND_BASE_CANDIDATES[0];

async function fetchWithBackendFallback(path, options = {}) {
  let lastError = null;

  for (const base of BACKEND_BASE_CANDIDATES) {
    const url = `${base}${path}`;
    try {
      const response = await fetch(url, options);
      if (response.status === 404) continue;
      ACTIVE_BACKEND_BASE = base;
      return response;
    } catch (err) {
      lastError = err;
    }
  }

  if (lastError) throw lastError;
  throw new Error("Backend not reachable on configured candidates.");
}
const CHAT_STORAGE_KEY = "pharma_chat_messages"; // legacy single-thread key
const CHAT_SESSIONS_STORAGE_KEY = "pharma_chat_sessions";
const ACTIVE_CHAT_ID_STORAGE_KEY = "pharma_active_chat_id";
const ORDERS_STORAGE_KEY = "pharma_orders";

function getCurrentUserPhone() {
  try {
    const raw = localStorage.getItem("cureos_user");
    if (!raw) return "";
    const parsed = JSON.parse(raw);
    return String(parsed?.phone || "").trim();
  } catch {
    return "";
  }
}

const WELCOME_MESSAGE =
  "Welcome to the Medico AI Pharmacist. How may I assist you with your medication or health-related queries today?";

const LEGACY_ANALYZING_MESSAGE =
  "Analyzing medicine, dosage, stock availability, and prescription rules...";
let typingIndicatorEl = null;
let activeChatId = null;

// Attach events only if elements exist
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (newChatBtn) newChatBtn.addEventListener("click", startNewChat);
if (submitPrescriptionBtn) {
  submitPrescriptionBtn.addEventListener("click", () => {
    prescriptionPhotoInput?.click();
  });
}
if (prescriptionPhotoInput) {
  prescriptionPhotoInput.addEventListener("change", handlePrescriptionPhotoSelected);
}

if (input) {
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
}

function generateChatId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
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

function getMessagesFromChatDom() {
  if (!chat) return [];

  return Array.from(chat.querySelectorAll(".bubble"))
    .filter((el) => !el.classList.contains("typing-indicator"))
    .map((el) => {
      const className = el.classList.contains("ai") ? "ai" : "user";
      const text =
        className === "ai"
          ? el.querySelector(".ai-text")?.innerText || ""
          : el.querySelector(".user-text")?.innerText || "";

      return { className, text };
    });
}

function getSavedSessions() {
  const raw = localStorage.getItem(CHAT_SESSIONS_STORAGE_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .filter((session) => session && typeof session.id === "string")
      .map((session) => ({
        id: session.id,
        messages: Array.isArray(session.messages)
          ? session.messages.filter(
              (msg) =>
                msg &&
                (msg.className === "ai" || msg.className === "user") &&
                typeof msg.text === "string"
            )
          : [],
        createdAt: session.createdAt || new Date().toISOString(),
        updatedAt: session.updatedAt || session.createdAt || new Date().toISOString(),
      }));
  } catch {
    return [];
  }
}

function saveSessions(sessions) {
  localStorage.setItem(CHAT_SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
}

function getSessionTitle(session) {
  if (!session || !Array.isArray(session.messages)) return "New Chat";

  const firstUserMsg = session.messages.find(
    (msg) => msg.className === "user" && msg.text.trim().length > 0
  );
  const firstAiMsg = session.messages.find(
    (msg) => msg.className === "ai" && msg.text.trim().length > 0
  );

  const rawTitle = (firstUserMsg?.text || firstAiMsg?.text || "New Chat").trim();
  return rawTitle.length > 28 ? `${rawTitle.slice(0, 28)}...` : rawTitle;
}

function renderChatHistory() {
  if (!chatHistoryList) return;

  const sessions = getSavedSessions().sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );

  chatHistoryList.innerHTML = "";

  sessions.forEach((session) => {
    const li = document.createElement("li");
    li.style.marginBottom = "8px";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = getSessionTitle(session);
    btn.style.width = "100%";
    btn.style.textAlign = "left";
    btn.style.padding = "8px 10px";
    btn.style.borderRadius = "8px";
    btn.style.border = "1px solid #e2e8f0";
    btn.style.background = session.id === activeChatId ? "#e0f2fe" : "#f8fafc";
    btn.style.cursor = "pointer";
    btn.style.fontSize = "0.9rem";

    btn.addEventListener("click", () => {
      openChatSession(session.id);
    });

    li.appendChild(btn);
    chatHistoryList.appendChild(li);
  });
}

function renderMessages(messages) {
  if (!chat) return;
  chat.innerHTML = "";

  messages.forEach((item) => {
    appendMessage(item.className, item.text, { persist: false });
  });

  chat.scrollTop = chat.scrollHeight;
}

function appendMessage(className, text, options = {}) {
  if (!chat) return;

  const msg = document.createElement("div");
  msg.className = `bubble ${className}`;

  if (className === "ai") {
    msg.innerHTML = `<span class="ai-logo" title="AI">AI</span><span class="ai-text">${String(
      text || ""
    ).replace(/\n/g, "<br>")}</span>`;
  } else {
    msg.innerHTML = `<span class="user-text">${String(text || "").replace(
      /\n/g,
      "<br>"
    )}</span>`;
  }

  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;

  if (options.persist !== false) {
    persistChat();
  }
}

function persistChat() {
  if (!chat || !activeChatId) return;

  const sessions = getSavedSessions();
  const idx = sessions.findIndex((s) => s.id === activeChatId);
  if (idx < 0) return;

  sessions[idx].messages = getMessagesFromChatDom();
  sessions[idx].updatedAt = new Date().toISOString();

  saveSessions(sessions);
  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(sessions[idx].messages));
  renderChatHistory();
}

function openChatSession(chatId) {
  if (!chat) return;

  const sessions = getSavedSessions();
  const target = sessions.find((session) => session.id === chatId);
  if (!target) return;

  activeChatId = target.id;
  localStorage.setItem(ACTIVE_CHAT_ID_STORAGE_KEY, activeChatId);
  renderMessages(target.messages);
  renderChatHistory();
}

function createChatSession(initialMessages) {
  const sessions = getSavedSessions();
  const now = new Date().toISOString();
  const newSession = {
    id: generateChatId(),
    messages: Array.isArray(initialMessages) ? initialMessages : [],
    createdAt: now,
    updatedAt: now,
  };

  sessions.push(newSession);
  saveSessions(sessions);

  activeChatId = newSession.id;
  localStorage.setItem(ACTIVE_CHAT_ID_STORAGE_KEY, activeChatId);

  return newSession;
}

function restoreChat() {
  if (!chat) return;

  let sessions = getSavedSessions();

  if (sessions.length === 0) {
    const legacyRaw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (legacyRaw) {
      try {
        const legacyMessages = JSON.parse(legacyRaw);
        if (Array.isArray(legacyMessages) && legacyMessages.length > 0) {
          createChatSession(legacyMessages);
          sessions = getSavedSessions();
        }
      } catch {
        // ignore broken legacy storage
      }
    }
  }

  if (sessions.length === 0) {
    createChatSession([{ className: "ai", text: WELCOME_MESSAGE }]);
    sessions = getSavedSessions();
  }

  const storedActiveId = localStorage.getItem(ACTIVE_CHAT_ID_STORAGE_KEY);
  const activeExists = sessions.some((session) => session.id === storedActiveId);
  if (activeExists) {
    activeChatId = storedActiveId;
  } else {
    sessions.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
    activeChatId = sessions[0].id;
    localStorage.setItem(ACTIVE_CHAT_ID_STORAGE_KEY, activeChatId);
  }

  openChatSession(activeChatId);
}

function startNewChat() {
  if (!chat) return;

  createChatSession([{ className: "ai", text: WELCOME_MESSAGE }]);
  openChatSession(activeChatId);
  if (input) input.value = "";
  setPrescriptionUploadVisibility(false);
}

// Clear chat history on login if needed
if (window.location.pathname.endsWith("chat.html")) {
  const loggedIn = localStorage.getItem("pharma_logged_in");
  if (
    loggedIn === "true" &&
    localStorage.getItem("pharma_clear_chat") === "true"
  ) {
    localStorage.removeItem(CHAT_STORAGE_KEY);
    localStorage.removeItem(CHAT_SESSIONS_STORAGE_KEY);
    localStorage.removeItem(ACTIVE_CHAT_ID_STORAGE_KEY);
    localStorage.setItem("pharma_clear_chat", "false");
  }
  
  // Update login status display
  const loginStatusEl = document.getElementById('login-status');
  if (loginStatusEl) {
    const username = localStorage.getItem('pharma_username');
    if (username && username !== 'GUEST') {
      loginStatusEl.textContent = `Logged in as: ${username}`;
      loginStatusEl.style.color = '#16a085';
    } else {
      loginStatusEl.innerHTML = '<a href="login.html" style="color: #dc3545; text-decoration: underline;">Not logged in - Click to login</a>';
    }
  }
}
restoreChat();
setPrescriptionUploadVisibility(false);

function showTypingIndicator() {
  if (!chat || typingIndicatorEl) return;

  const msg = document.createElement("div");
  msg.className = "bubble ai typing-indicator";
  msg.innerHTML = `
    <span class="ai-logo" title="AI">AI</span>
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

async function getInventoryPriceMap() {
  try {
    const res = await fetchWithBackendFallback("/inventory");
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

async function trackPlacedOrderFromReply(replyText, contextMessage = "") {
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
  await persistOrderToBackend(newOrder, contextMessage);

  const phone = getCurrentUserPhone();
  if (phone) {
    try {
      await fetchWithBackendFallback("/users/order-event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          phone,
          quantity: parsed.quantity,
        }),
      });
    } catch {
      // Order tracking in UI should continue even if backend sync fails.
    }
  }
}

function inferDosageFrequencyFromText(text) {
  const msg = String(text || "").toLowerCase();
  if (!msg) return "once daily";
  if (/\b(as needed|if needed|prn|sos)\b/.test(msg)) return "as needed";
  if (/\b(twice daily|2x daily|bid|bd)\b/.test(msg)) return "twice daily";
  if (/\b(thrice daily|three times daily|3x daily|tid|tds)\b/.test(msg)) return "three times daily";
  if (/\b(four times daily|4x daily|qid)\b/.test(msg)) return "four times daily";
  if (/\bevery\s*12\s*hours?\b/.test(msg)) return "every 12 hours";
  if (/\bevery\s*8\s*hours?\b/.test(msg)) return "every 8 hours";
  if (/\bevery\s*6\s*hours?\b/.test(msg)) return "every 6 hours";
  return "once daily";
}

function getLastUserMessageText() {
  if (!chat) return "";
  const userBubbles = Array.from(chat.querySelectorAll(".bubble.user .user-text"));
  if (!userBubbles.length) return "";
  return String(userBubbles[userBubbles.length - 1].innerText || "").trim();
}

async function persistOrderToBackend(orderRecord, contextMessage = "") {
  if (!orderRecord) return;
  const userRaw = localStorage.getItem("cureos_user");
  let username = localStorage.getItem("pharma_username") || "GUEST";
  let phone = getCurrentUserPhone();
  try {
    if (userRaw) {
      const parsed = JSON.parse(userRaw);
      username = parsed?.username || username;
      phone = parsed?.phone || phone;
    }
  } catch {
    // Use fallback values.
  }

  if (!phone) return;

  const dosage_frequency = inferDosageFrequencyFromText(contextMessage || getLastUserMessageText());
  const payload = {
    patient_id: username,
    username,
    phone,
    medicine_name: orderRecord.medicine_name,
    quantity: Number(orderRecord.quantity || 0),
    dosage_frequency,
    ordered_at: new Date().toISOString(),
    unit_price: Number(orderRecord.unit_price || 0),
    total_price: Number(orderRecord.total_price || 0),
    status: "Placed",
    source: "chat-confirmation",
  };

  try {
    await fetchWithBackendFallback("/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    // Keep local order history as fallback even if backend write fails.
  }
}

function setPrescriptionUploadVisibility(isVisible) {
  if (!submitPrescriptionBtn) return;
  submitPrescriptionBtn.style.display = isVisible ? "inline-flex" : "none";
}

function fileToDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Failed to read image file."));
    reader.readAsDataURL(file);
  });
}

async function handlePrescriptionPhotoSelected(event) {
  const file = event?.target?.files?.[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    appendMessage("ai", "Please upload an image file for the prescription.");
    event.target.value = "";
    return;
  }

  try {
    const imageData = await fileToDataURL(file);
    appendMessage("user", "Add Prescription");
    appendMessage("ai", "Uploading prescription photo...");

    const res = await fetchWithBackendFallback("/prescription/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_data: imageData,
        filename: file.name || "prescription.jpg",
      }),
    });

    if (!res.ok) {
      let errText = "Unable to submit prescription.";
      try {
        const errJson = await res.json();
        errText = errJson?.detail || errText;
      } catch {
        const raw = await res.text();
        if (raw) errText = raw;
      }
      appendMessage("ai", `Prescription submission failed: ${errText}`);
      return;
    }

    const data = await res.json();
    const replyText = sanitizeAiText(data.reply || "Prescription submitted successfully.");
    appendMessage("ai", replyText || "Prescription submitted successfully.");
    setPrescriptionUploadVisibility(false);
    await trackPlacedOrderFromReply(replyText);
  } catch (err) {
    appendMessage("ai", "Could not submit prescription. Please try again.");
    console.error(err);
  } finally {
    event.target.value = "";
  }
}

async function startUpiIntentPayment(payment) {
  if (!payment) {
    appendMessage("ai", "Payment details missing. Please try placing the order again.");
    return;
  }

  let orderPayload;
  try {
    const createRes = await fetchWithBackendFallback("/payment/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        medicine_name: payment.medicine_name,
        quantity: payment.quantity,
        total_price: payment.total_price,
        currency: payment.currency || "INR",
      }),
    });

    if (!createRes.ok) {
      let errText = "Unable to initialize payment.";
      try {
        const errJson = await createRes.json();
        errText = errJson?.detail || errText;
      } catch {
        const raw = await createRes.text();
        if (raw) errText = raw;
      }
      appendMessage("ai", `Payment initialization failed: ${errText}`);
      return;
    }

    orderPayload = await createRes.json();
  } catch (err) {
    appendMessage("ai", "Could not initialize payment. Please try again.");
    console.error(err);
    return;
  }

  if (orderPayload.provider !== "upi_intent") {
    appendMessage(
      "ai",
      "Payment mode mismatch. Backend is expected to return UPI intent."
    );
    return;
  }

  const upiLink = orderPayload.upi_link || "";
  const qrUrl = orderPayload.qr_url || "";
  const amountText = Number(orderPayload.amount || 0) / 100;

  const qrText = qrUrl ? `\nQR: ${qrUrl}` : "";
  appendMessage(
    "ai",
    `UPI Intent Payment\nAmount: INR ${amountText.toFixed(2)}\nUPI Link: ${upiLink}${qrText}\nComplete payment in your UPI app, then click OK to place your order.`
  );

  const confirmPaid = window.confirm(
    `After paying INR ${amountText.toFixed(2)} using your UPI app, click OK to place the order.`
  );
  if (!confirmPaid) {
    appendMessage("ai", "Payment cancelled. Order was not placed.");
    return;
  }

  try {
    const confirmRes = await fetchWithBackendFallback("/payment/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        medicine_name: payment.medicine_name,
        quantity: payment.quantity,
        payment_mode: "upi_intent",
        upi_confirmed: true,
      }),
    });
    if (!confirmRes.ok) {
      let errText = "Could not confirm UPI payment.";
      try {
        const errJson = await confirmRes.json();
        errText = errJson?.detail || errText;
      } catch {
        const raw = await confirmRes.text();
        if (raw) errText = raw;
      }
      appendMessage("ai", `UPI payment confirmation failed: ${errText}`);
      return;
    }
    const confirmData = await confirmRes.json();
    appendMessage("ai", confirmData.reply || "Order placed.");
    await trackPlacedOrderFromReply(confirmData.reply || "");
  } catch (err) {
    appendMessage("ai", "Could not confirm UPI payment. Please try again.");
    console.error(err);
  }
}

async function sendMessage(textFromVoice) {
  const rawMessage =
    typeof textFromVoice === "string" ? textFromVoice : input?.value ?? "";
  const message = String(rawMessage).trim();
  const hasVisibleMessage = message.length > 0;

  const username = localStorage.getItem("pharma_username") || "GUEST";
  const userData = JSON.parse(localStorage.getItem("cureos_user") || '{}');
  const phone = userData.phone || null;
  
  // Warn user if not logged in
  if (username === "GUEST") {
    const shouldLogin = confirm("You are not logged in. Orders will be saved as GUEST without your contact info.\n\nDo you want to login/signup first?");
    if (shouldLogin) {
      window.location.href = 'login.html';
      return;
    }
  }

  if (hasVisibleMessage) {
    appendMessage("user", message);
  }

  if (input) input.value = "";
  if (sendBtn) sendBtn.disabled = true;
  showTypingIndicator();

  try {
    console.log('Sending chat request:', { username, phone, message });
    
    const res = await fetchWithBackendFallback("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: hasVisibleMessage ? message : "",
        user_id: username,
        phone: phone,
        chat_id: activeChatId || null,
      }),
    });

    if (!res.ok) {
      hideTypingIndicator();
      appendMessage("ai", `Backend error: ${res.status} ${res.statusText}`);
      return;
    }

    const data = await res.json();
    hideTypingIndicator();
    const replyText = sanitizeAiText(data.reply || "No reply received from backend.");
    appendMessage("ai", replyText || "No reply received from backend.");
    setPrescriptionUploadVisibility(Boolean(data.prescription_required));
    await trackPlacedOrderFromReply(replyText, message);
  } catch (err) {
    hideTypingIndicator();
    appendMessage(
      "ai",
      `Cannot connect to backend. Set localStorage PHARMA_API_BASE (example: http://127.0.0.1:8000). Tried: ${BACKEND_BASE_CANDIDATES.join(", ")}`
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
  recognition.continuous = false;
  recognition.interimResults = false;

  const micBtn = document.querySelector("#mic-btn");

  if (micBtn) {
    micBtn.addEventListener("click", () => {
      try {
        recognition.start();
      } catch (err) {
        appendMessage("ai", "Microphone could not start. Check browser mic permission.");
      }
    });
  }

  recognition.onresult = (e) => {
    const voiceText = e.results[0][0].transcript;
    sendMessage(voiceText);
  };

  recognition.onerror = () => {
    appendMessage("ai", "Voice input failed. Allow microphone permission and try again.");
  };
} else {
  const micBtn = document.querySelector("#mic-btn");
  if (micBtn) micBtn.style.display = "none";
}
