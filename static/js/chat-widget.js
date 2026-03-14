(function () {
  const API_URL = "/api/chat";
  const STORAGE_KEY = "chat_session_id";
  const HISTORY_KEY = "chat_session_history";
  const MAX_HISTORY = 30;
  const MAX_MESSAGE_LENGTH = 500;
  const GREETING =
    "Ola! Posso ajudar com agendamento, contato, endereco, convenios e outras informacoes administrativas. " +
    "Este chat nao faz diagnostico nem atendimento de urgencia.";

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else node.setAttribute(k, v);
    });
    children.forEach((c) => node.appendChild(c));
    return node;
  }

  function getSessionId() {
    let sid = localStorage.getItem(STORAGE_KEY);
    if (!sid) {
      sid = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
      localStorage.setItem(STORAGE_KEY, sid);
    }
    return sid;
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      const data = JSON.parse(raw || "[]");
      if (Array.isArray(data)) return data;
    } catch (err) {
      console.warn("Chat history invalido", err);
    }
    return [];
  }

  function saveHistory(history) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }

  let history = loadHistory();

  function pushHistory(role, content) {
    history.push({ role, content });
    if (history.length > MAX_HISTORY) history = history.slice(-MAX_HISTORY);
    saveHistory(history);
  }

  async function sendMessage(text) {
    const payload = {
      session_id: getSessionId(),
      message: text,
      history: history.slice(-MAX_HISTORY),
    };
    const resp = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8", Accept: "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) throw new Error(data.error || "Falha ao responder");
    return data;
  }

  const root = el("div", { class: "chat-root" });
  const button = el("button", { class: "chat-btn", type: "button", ariaLabel: "Abrir chat", title: "Chat" }, [
    document.createTextNode("Chat")
  ]);

  const panel = el("div", { class: "chat-panel chat-hidden" });
  const header = el("div", { class: "chat-header" });
  const headerTitle = el("div", {
    class: "chat-header-title",
    html: "<strong>Atendimento</strong><span class='chat-sub'>Informacoes e agendamentos</span>"
  });
  const resetBtn = el("button", { class: "chat-reset", type: "button" }, [document.createTextNode("Novo assunto")]);
  header.appendChild(headerTitle);
  header.appendChild(resetBtn);
  const messages = el("div", { class: "chat-messages" });

  const form = el("form", { class: "chat-form" });
  const input = el("input", {
    class: "chat-input",
    type: "text",
    placeholder: "Digite sua mensagem...",
    maxlength: String(MAX_MESSAGE_LENGTH)
  });
  const sendBtn = el("button", { class: "chat-send", type: "submit" }, [document.createTextNode("Enviar")]);
  const status = el("div", { class: "chat-status" });

  form.appendChild(input);
  form.appendChild(sendBtn);

  panel.appendChild(header);
  panel.appendChild(messages);
  panel.appendChild(status);
  panel.appendChild(form);

  root.appendChild(panel);
  root.appendChild(button);
  document.body.appendChild(root);

  function addMsg(role, text) {
    const bubble = el("div", { class: "chat-bubble " + (role === "user" ? "chat-user" : "chat-bot") });
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  function setStatus(text) {
    status.textContent = text || "";
  }

  function renderGreeting() {
    addMsg("bot", GREETING);
    pushHistory("assistant", GREETING);
  }

  function resetConversation(withGreeting = true) {
    history = [];
    localStorage.removeItem(HISTORY_KEY);
    localStorage.removeItem(STORAGE_KEY);
    messages.innerHTML = "";
    if (withGreeting) {
      renderGreeting();
    }
  }

  function renderHistory() {
    messages.innerHTML = "";
    history.forEach((item) => addMsg(item.role === "user" ? "user" : "bot", item.content));
  }

  button.addEventListener("click", () => {
    panel.classList.toggle("chat-hidden");
    if (!panel.classList.contains("chat-hidden")) input.focus();
    if (messages.childElementCount === 0) {
      if (history.length === 0) {
        renderGreeting();
      } else {
        renderHistory();
      }
    }
  });

  resetBtn.addEventListener("click", () => {
    resetConversation(true);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = (input.value || "").trim();
    if (!text) return;
    if (text.length > MAX_MESSAGE_LENGTH) {
      setStatus(`Limite de ${MAX_MESSAGE_LENGTH} caracteres por mensagem.`);
      return;
    }

    addMsg("user", text);
    pushHistory("user", text);
    input.value = "";
    setStatus("Digitando...");

    try {
      const data = await sendMessage(text);
      if (data.reset_history) {
        resetConversation(false);
      }
      addMsg("bot", data.reply);
      pushHistory("assistant", data.reply);
      setStatus("");
    } catch (err) {
      addMsg("bot", "Tive um problema ao responder. Tente novamente em instantes.");
      setStatus("");
      console.error(err);
    }
  });
})();
