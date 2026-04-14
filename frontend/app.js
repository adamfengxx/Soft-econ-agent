const storageKeys = {
  apiBase: "econagent_api_base",
  threadId: "econagent_thread_id",
  userId: "econagent_user_id",
};

const state = {
  apiBase: localStorage.getItem(storageKeys.apiBase) || "http://127.0.0.1:8000",
  currentThreadId: localStorage.getItem(storageKeys.threadId) || "",
  userId: localStorage.getItem(storageKeys.userId) || "",
  threads: [],
  tasks: [],
  messages: [],
  assistantMessageId: "",
  isStreaming: false,
};

const els = {
  apiBase: document.querySelector("#apiBase"),
  saveApiBase: document.querySelector("#saveApiBase"),
  newThread: document.querySelector("#newThread"),
  refreshThreads: document.querySelector("#refreshThreads"),
  threadList: document.querySelector("#threadList"),
  threadTitle: document.querySelector("#threadTitle"),
  connectionStatus: document.querySelector("#connectionStatus"),
  userIdDisplay: document.querySelector("#userIdDisplay"),
  summaryText: document.querySelector("#summaryText"),
  messageList: document.querySelector("#messageList"),
  composer: document.querySelector("#composer"),
  messageInput: document.querySelector("#messageInput"),
  sendButton: document.querySelector("#sendButton"),
  taskBoard: document.querySelector("#taskBoard"),
  eventFeed: document.querySelector("#eventFeed"),
  clearTasks: document.querySelector("#clearTasks"),
  clearEvents: document.querySelector("#clearEvents"),
  messageTemplate: document.querySelector("#messageTemplate"),
  threadTemplate: document.querySelector("#threadTemplate"),
  taskTemplate: document.querySelector("#taskTemplate"),
};

init();

function init() {
  els.apiBase.value = state.apiBase;
  setConnectionStatus("Idle");
  syncUserBadge();
  bindEvents();
  renderTasks();
  renderEvents([]);
  loadThreads();

  if (state.currentThreadId) {
    loadHistory(state.currentThreadId);
  } else {
    renderMessages();
  }
}

function bindEvents() {
  els.saveApiBase.addEventListener("click", () => {
    state.apiBase = normalizeBaseUrl(els.apiBase.value);
    localStorage.setItem(storageKeys.apiBase, state.apiBase);
    addEvent("config", { apiBase: state.apiBase });
    loadThreads();
  });

  els.newThread.addEventListener("click", resetThread);
  els.refreshThreads.addEventListener("click", loadThreads);
  els.clearTasks.addEventListener("click", () => {
    state.tasks = [];
    renderTasks();
  });
  els.clearEvents.addEventListener("click", () => renderEvents([]));

  els.composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = els.messageInput.value.trim();
    if (!message || state.isStreaming) {
      return;
    }
    await sendMessage(message);
  });
}

function normalizeBaseUrl(value) {
  return (value || "").trim().replace(/\/+$/, "") || "http://127.0.0.1:8000";
}

function setConnectionStatus(label, tone = "") {
  els.connectionStatus.textContent = label;
  els.connectionStatus.className = `pill${tone ? ` ${tone}` : ""}`;
}

function syncUserBadge() {
  if (!state.userId) {
    els.userIdDisplay.textContent = "No user yet";
    return;
  }
  els.userIdDisplay.textContent = `User ${state.userId.slice(0, 8)}`;
}

function resetThread() {
  state.currentThreadId = "";
  state.messages = [];
  state.tasks = [];
  state.assistantMessageId = "";
  localStorage.removeItem(storageKeys.threadId);
  els.threadTitle.textContent = "New conversation";
  els.summaryText.textContent = "No summary yet. Start a conversation to build thread memory.";
  renderMessages();
  renderTasks();
}

async function loadThreads() {
  if (!state.userId) {
    renderThreadList([]);
    return;
  }

  try {
    const response = await fetch(
      `${state.apiBase}/api/threads?user_id=${encodeURIComponent(state.userId)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to load threads: ${response.status}`);
    }
    const data = await response.json();
    state.threads = data.threads || [];
    renderThreadList(state.threads);
  } catch (error) {
    addEvent("error", { message: String(error) });
  }
}

async function loadHistory(threadId) {
  try {
    const response = await fetch(`${state.apiBase}/api/history/${encodeURIComponent(threadId)}`);
    if (!response.ok) {
      throw new Error(`Failed to load history: ${response.status}`);
    }
    const data = await response.json();
    state.currentThreadId = threadId;
    localStorage.setItem(storageKeys.threadId, threadId);
    els.threadTitle.textContent = data.title || "Untitled thread";
    els.summaryText.textContent =
      data.summary || "No summary yet. This thread will build memory as messages accumulate.";
    state.messages = (data.messages || []).map((message, index) => ({
      id: `${message.role}-${index}-${message.created_at || Date.now()}`,
      role: message.role,
      content: message.content,
    }));
    renderMessages();
    renderThreadList(state.threads);
  } catch (error) {
    addEvent("error", { message: String(error) });
  }
}

async function sendMessage(message) {
  state.isStreaming = true;
  setConnectionStatus("Streaming", "running");
  els.sendButton.disabled = true;

  const userMessage = {
    id: `user-${Date.now()}`,
    role: "user",
    content: message,
  };
  const assistantMessage = {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
  };

  state.messages.push(userMessage, assistantMessage);
  state.assistantMessageId = assistantMessage.id;
  renderMessages();
  els.messageInput.value = "";

  try {
    const response = await fetch(`${state.apiBase}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        thread_id: state.currentThreadId || null,
        user_id: state.userId || null,
      }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const nextThreadId = response.headers.get("X-Thread-Id");
    const nextUserId = response.headers.get("X-User-Id");

    if (nextThreadId) {
      state.currentThreadId = nextThreadId;
      localStorage.setItem(storageKeys.threadId, nextThreadId);
    }
    if (nextUserId) {
      state.userId = nextUserId;
      localStorage.setItem(storageKeys.userId, nextUserId);
      syncUserBadge();
    }

    await readSseStream(response.body);
    await loadThreads();

    if (state.currentThreadId) {
      const active = state.threads.find((thread) => thread.id === state.currentThreadId);
      els.threadTitle.textContent = active?.title || "Current conversation";
    }
  } catch (error) {
    appendAssistantText(`\n[Frontend error] ${String(error)}`);
    addEvent("error", { message: String(error) });
  } finally {
    state.isStreaming = false;
    setConnectionStatus("Idle");
    els.sendButton.disabled = false;
  }
}

async function readSseStream(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const normalized = buffer.replace(/\r\n/g, "\n");
    const chunks = normalized.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const parsed = parseSseChunk(chunk);
      if (parsed) {
        handleServerEvent(parsed.event, parsed.data);
      }
    }
  }
}

function parseSseChunk(chunk) {
  const lines = chunk.split(/\r?\n/);
  let event = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  let data = {};
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    data = { raw: dataLines.join("\n") };
  }

  return { event, data };
}

function handleServerEvent(event, data) {
  if (event === "chat_token" || event === "report_token") {
    appendAssistantText(data.token || "");
  }

  if (event === "plan_generated") {
    state.tasks = (data.tasks || []).map((task) => ({
      ...task,
      status: task.status || "pending",
    }));
    renderTasks();
  }

  if (event === "task_status_update") {
    state.tasks = state.tasks.map((task) =>
      task.id === data.task_id ? { ...task, status: data.status } : task
    );
    renderTasks();
  }

  if (event === "done") {
    setConnectionStatus("Completed");
    if (state.currentThreadId) {
      loadHistory(state.currentThreadId);
    }
  }

  addEvent(event, data);
}

function appendAssistantText(text) {
  const assistant = state.messages.find((message) => message.id === state.assistantMessageId);
  if (!assistant) {
    return;
  }
  assistant.content += text;
  renderMessages();
}

function renderMessages() {
  els.messageList.innerHTML = "";

  if (!state.messages.length) {
    els.messageList.innerHTML = '<div class="empty-state">No messages yet.</div>';
    return;
  }

  for (const message of state.messages) {
    const fragment = els.messageTemplate.content.cloneNode(true);
    const node = fragment.querySelector(".message");
    node.dataset.role = message.role;
    fragment.querySelector(".message-meta").textContent =
      message.role === "user" ? "You" : "Assistant";
    fragment.querySelector(".message-bubble").textContent = message.content || " ";
    els.messageList.appendChild(fragment);
  }

  els.messageList.scrollTop = els.messageList.scrollHeight;
}

function renderThreadList(threads) {
  els.threadList.innerHTML = "";

  if (!threads.length) {
    els.threadList.innerHTML =
      '<div class="empty-state">No saved threads yet. Start a new chat to create one.</div>';
    return;
  }

  for (const thread of threads) {
    const fragment = els.threadTemplate.content.cloneNode(true);
    const button = fragment.querySelector(".thread-item");
    button.dataset.threadId = thread.id;
    if (thread.id === state.currentThreadId) {
      button.classList.add("active");
    }
    fragment.querySelector(".thread-item-title").textContent =
      thread.title || "Untitled thread";
    fragment.querySelector(".thread-item-meta").textContent =
      `${thread.message_count} messages`;
    button.addEventListener("click", () => loadHistory(thread.id));
    els.threadList.appendChild(fragment);
  }
}

function renderTasks() {
  els.taskBoard.innerHTML = "";

  if (!state.tasks.length) {
    els.taskBoard.innerHTML =
      '<div class="empty-state">Task planning events will appear here.</div>';
    return;
  }

  for (const task of state.tasks) {
    const fragment = els.taskTemplate.content.cloneNode(true);
    fragment.querySelector(".task-id").textContent = task.id;
    const status = fragment.querySelector(".task-status");
    status.textContent = task.status || "pending";
    status.classList.add(task.status || "pending");
    fragment.querySelector(".task-description").textContent = task.description;
    els.taskBoard.appendChild(fragment);
  }
}

function addEvent(eventName, data) {
  const currentItems = Array.from(els.eventFeed.children).filter(
    (child) => !child.classList.contains("empty-state")
  );
  const item = document.createElement("article");
  item.className = "event-item";
  item.innerHTML = `
    <div class="event-name">${escapeHtml(eventName)}</div>
    <pre class="event-data">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
  `;
  currentItems.unshift(item);
  renderEvents(currentItems.slice(0, 40));
}

function renderEvents(items) {
  els.eventFeed.innerHTML = "";

  if (!items.length) {
    els.eventFeed.innerHTML =
      '<div class="empty-state">Server events will stream in here.</div>';
    return;
  }

  for (const item of items) {
    els.eventFeed.appendChild(item);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
