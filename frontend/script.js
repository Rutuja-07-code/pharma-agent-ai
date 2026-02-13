// Select elements
const sendBtn = document.querySelector("button");
const input = document.querySelector("input");
const chat = document.querySelector(".chat");

// Send message on button click
sendBtn.addEventListener("click", sendMessage);

// Send message on Enter key
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});

function sendMessage() {
  const message = input.value.trim();
  if (message === "") return;

  // User message
  const userMsg = document.createElement("div");
  userMsg.className = "user";
  userMsg.innerText = message;
  chat.appendChild(userMsg);

  input.value = "";
  chat.scrollTop = chat.scrollHeight;

  // AI thinking indicator
  setTimeout(() => {
    const aiMsg = document.createElement("div");
    aiMsg.className = "ai";
    aiMsg.innerText =
      "Analyzing medicine, dosage, stock availability, and prescription rules…";
    chat.appendChild(aiMsg);
    chat.scrollTop = chat.scrollHeight;
  }, 700);
}
