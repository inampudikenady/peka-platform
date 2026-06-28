const askForm = document.getElementById("askForm");
const followupForm = document.getElementById("followupForm");
const questionInput = document.getElementById("question");
const followupInput = document.getElementById("followup");
const conversation = document.getElementById("conversation");
const hero = document.getElementById("hero");
const historyPanel = document.getElementById("historyPanel");
const historyOverlay = document.getElementById("historyOverlay");
const askBtn = document.getElementById("askBtn");
const followupBtn = followupForm.querySelector("button[type='submit']");

const THINKING_STAGES = [
  "Understanding your question",
  "Checking available sources",
  "Searching operational context",
  "Preparing response",
];

let conversationId = createConversationId();
let requestInFlight = false;

if (window.marked) {
  marked.setOptions({
    breaks: true,
    gfm: true,
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function createConversationId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }

  return `conversation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function renderMarkdown(text) {
  const cleaned = cleanAnswerText(text);

  if (window.marked && typeof marked.parse === "function") {
    return marked.parse(cleaned);
  }

  return escapeHtml(cleaned).replace(/\n/g, "<br>");
}

function setSending(isSending) {
  requestInFlight = isSending;
  askBtn.disabled = isSending;
  followupBtn.disabled = isSending;
}

function showConversation() {
  hero.classList.add("hidden");
  conversation.classList.remove("hidden");
  followupForm.classList.remove("hidden");
}

function addMessage(role, text, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  if (options.error) wrapper.classList.add("error");

  const roleEl = document.createElement("div");
  roleEl.className = "role";
  roleEl.textContent = role === "user" ? "You" : "PEKA";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (options.markdown) {
    bubble.classList.add("markdown");
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.innerHTML = escapeHtml(text);
  }

  wrapper.appendChild(roleEl);
  wrapper.appendChild(bubble);
  conversation.appendChild(wrapper);
  wrapper.scrollIntoView({ behavior: "smooth", block: "end" });
  return wrapper;
}

function addThinkingMessage() {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";

  const roleEl = document.createElement("div");
  roleEl.className = "role";
  roleEl.textContent = "PEKA";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `
    <div class="thinking">
      <span class="pulse" aria-hidden="true"></span>
      <span><span class="thinking-text">${THINKING_STAGES[0]}</span><span class="dots" aria-hidden="true"></span></span>
    </div>
  `;

  wrapper.appendChild(roleEl);
  wrapper.appendChild(bubble);
  conversation.appendChild(wrapper);
  wrapper.scrollIntoView({ behavior: "smooth", block: "end" });

  const textEl = wrapper.querySelector(".thinking-text");
  let index = 0;
  const interval = window.setInterval(() => {
    index = (index + 1) % THINKING_STAGES.length;
    textEl.textContent = THINKING_STAGES[index];
  }, 1900);

  return {
    remove() {
      window.clearInterval(interval);
      wrapper.remove();
    },
  };
}

function cleanAnswerText(answer) {
  if (!answer) return "";

  return answer
    .replace(/\/Users\/[^\s)\]}>"']+/g, "Knowledge source")
    .replace(/\bSources?\s+Source\s+\d+\s*:\s*/gi, "Sources: ")
    .replace(/(?:^|\n)\s*Source\s+\d+\s*:\s*(?:Knowledge source|\/Users\/[^\n]+)\s*/gi, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function createTimeoutController(ms) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), ms);

  return {
    signal: controller.signal,
    clear() {
      window.clearTimeout(timeout);
    },
  };
}

async function submitQuestion(text) {
  const question = text.trim();
  if (!question || requestInFlight) return;

  showConversation();
  addMessage("user", question);
  setSending(true);

  const thinking = addThinkingMessage();
  const timeout = createTimeoutController(120000);

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: conversationId }),
      signal: timeout.signal,
    });

    let data = {};
    try {
      data = await res.json();
    } catch {
      data = {};
    }

    thinking.remove();

    if (!res.ok) {
      addErrorCard(data.detail || data.error || `Request failed with status ${res.status}.`);
      return;
    }

    addMessage("assistant", data.answer || "No answer returned.", { markdown: true });
    saveHistory(question);
  } catch (err) {
    thinking.remove();
    const isTimeout = err.name === "AbortError";
    addErrorCard(
      isTimeout
        ? "PEKA took longer than 120 seconds to respond. Please try again with a narrower question."
        : "Unable to reach PEKA API. Please check that the backend is running and try again."
    );
  } finally {
    timeout.clear();
    setSending(false);
    followupInput.focus();
  }
}

function addErrorCard(message) {
  addMessage("assistant", `# Request Error\n\n${message}`, {
    markdown: true,
    error: true,
  });
}

function saveHistory(title) {
  const existing = JSON.parse(localStorage.getItem("peka_history") || "[]");
  const current = existing.filter((item) => item.id !== conversationId);

  current.unshift({
    id: conversationId,
    title,
    updated: new Date().toISOString(),
  });

  localStorage.setItem("peka_history", JSON.stringify(current.slice(0, 20)));
}

function loadHistory() {
  const list = document.getElementById("historyList");
  const items = JSON.parse(localStorage.getItem("peka_history") || "[]");

  if (!items.length) {
    list.innerHTML = '<div class="empty">No saved history yet.</div>';
    return;
  }

  list.innerHTML = items.map((item) => `
    <div class="history-item">
      <span class="history-title">${escapeHtml(item.title)}</span>
      <span class="history-date">${new Date(item.updated).toLocaleString()}</span>
    </div>
  `).join("");
}

function openHistory() {
  loadHistory();
  historyPanel.classList.remove("hidden");
  historyOverlay.classList.remove("hidden");
}

function closeHistory() {
  historyPanel.classList.add("hidden");
  historyOverlay.classList.add("hidden");
}

function resetChat() {
  conversationId = createConversationId();
  conversation.innerHTML = "";
  conversation.classList.add("hidden");
  followupForm.classList.add("hidden");
  hero.classList.remove("hidden");
  questionInput.focus();
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 170)}px`;
}

[questionInput, followupInput].forEach((input) => {
  input.addEventListener("input", () => autoResize(input));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      input.form.requestSubmit();
    }
  });
});

askForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = questionInput.value;
  questionInput.value = "";
  autoResize(questionInput);
  submitQuestion(text);
});

followupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = followupInput.value;
  followupInput.value = "";
  autoResize(followupInput);
  submitQuestion(text);
});

document.querySelectorAll("[data-question]").forEach((btn) => {
  btn.addEventListener("click", () => submitQuestion(btn.dataset.question));
});

document.getElementById("newChatBtn").addEventListener("click", resetChat);
document.getElementById("historyBtn").addEventListener("click", openHistory);
document.getElementById("closeHistory").addEventListener("click", closeHistory);
historyOverlay.addEventListener("click", closeHistory);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeHistory();
});
