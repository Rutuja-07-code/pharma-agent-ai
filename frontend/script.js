const sendBtn = document.querySelector(".send-btn");
const micBtn = document.querySelector(".mic-btn");
const input = document.querySelector("input");
const chat = document.querySelector(".chat-box");

// Send via button or enter
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

function sendMessage(textFromVoice) {
  const message = textFromVoice || input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  input.value = "";

  setTimeout(() => {
    addMessage(
      "Analyzing medicine, dosage, stock availability, and prescription rules…",
      "ai"
    );
  }, 600);
}

function addMessage(text, type) {
  const msg = document.createElement("div");
  msg.className = type;
  msg.innerText = text;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

/* VOICE COMMAND */
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";

  micBtn.addEventListener("click", () => recognition.start());

  recognition.onresult = e => {
    const voiceText = e.results[0][0].transcript;
    sendMessage(voiceText);
  };
} else {
  micBtn.style.display = "none";
}
