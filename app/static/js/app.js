(() => {
  const STATES = {
    INITIALIZE: "initialize",
    RECORDING: "recording",
    READY: "ready",
  };

  const ui = {
    button: document.getElementById("mainActionButton"),
    icon: document.getElementById("mainActionIcon"),
    label: document.getElementById("mainActionLabel"),
    status: document.getElementById("statusText"),
    language: document.getElementById("language"),
    chat: document.getElementById("chat"),
  };

  let state = STATES.INITIALIZE;

  function setState(next) {
    state = next;
    ui.button.classList.remove("state-initialize", "state-recording", "state-ready");

    if (next === STATES.INITIALIZE) {
      ui.button.classList.add("state-initialize");
      ui.icon.textContent = "▶";
      ui.label.textContent = "Initialize";
      ui.status.textContent = "State: Initialize";
    } else if (next === STATES.RECORDING) {
      ui.button.classList.add("state-recording");
      ui.icon.textContent = "⏺";
      ui.label.textContent = "Recording";
      ui.status.textContent = "State: Recording (scaffold only)";
    } else {
      ui.button.classList.add("state-ready");
      ui.icon.textContent = "➤";
      ui.label.textContent = "Ready to Send";
      ui.status.textContent = "State: Ready to Send";
    }
  }

  function renderChat(chat) {
    if (!Array.isArray(chat)) return;
    ui.chat.innerHTML = "";
    chat.forEach((msg) => {
      const bubble = document.createElement("div");
      bubble.className = `chat-bubble ${msg.role === "user" ? "chat-user" : "chat-assistant"}`;
      bubble.textContent = msg.content;
      ui.chat.appendChild(bubble);
    });
    ui.chat.scrollTop = ui.chat.scrollHeight;
  }

  async function initializeSession() {
    const fd = new FormData();
    fd.append("language", ui.language.value);
    const response = await fetch("/initialize", { method: "POST", body: fd });
    const data = await response.json();
    renderChat(data.chat);
    setState(STATES.RECORDING);
  }

  async function sendAudioPlaceholder() {
    const fd = new FormData();
    const response = await fetch("/upload-audio", { method: "POST", body: fd });
    const data = await response.json();
    renderChat(data.chat);
    setState(STATES.RECORDING);
  }

  ui.button.addEventListener("click", async () => {
    if (state === STATES.INITIALIZE) {
      await initializeSession();
      return;
    }

    if (state === STATES.RECORDING) {
      // Step 1 scaffold: microphone logic intentionally not implemented yet.
      setState(STATES.READY);
      return;
    }

    await sendAudioPlaceholder();
  });

  setState(STATES.INITIALIZE);
})();
