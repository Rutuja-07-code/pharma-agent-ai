// Select elements
const sendBtn = document.querySelector("button");
const input = document.querySelector("input");
const chat = document.querySelector(".chat");
const BACKEND_URL = "http://127.0.0.1:8000/chat";

// Send message on button click
sendBtn.addEventListener("click", sendMessage);

// Send message on Enter key
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});

function appendMessage(className, text) {
  const msg = document.createElement("div");
  msg.className = className;
  msg.innerText = text;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

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
