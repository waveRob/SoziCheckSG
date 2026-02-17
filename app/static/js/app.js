(() => {
  const STATES = {
    INIT: "init",
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
    typingArea: document.getElementById("typingArea"),
    typedInput: document.getElementById("typedInput"),
  };

  let state = STATES.INIT;
  let isWorking = false;

  function appendMessage(role, content) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role === "user" ? "chat-user" : "chat-assistant"}`;
    bubble.textContent = content;
    ui.chat.appendChild(bubble);
    ui.chat.scrollTop = ui.chat.scrollHeight;
  }

  function setWorking(working) {
    isWorking = working;
    ui.button.disabled = working;
    ui.button.classList.toggle("is-loading", working);

    if (working) {
      ui.icon.textContent = "⏳";
      ui.label.textContent = "Working…";
    } else {
      setState(state);
    }
  }

  function setState(next) {
    state = next;
    ui.button.classList.remove("state-init", "state-recording", "state-ready");

    if (next === STATES.INIT) {
      ui.button.classList.add("state-init");
      ui.icon.textContent = "▶";
      ui.label.textContent = "Initialize";
      ui.status.textContent = "State: init";
      ui.typingArea.classList.add("hidden");
      ui.typedInput.value = "";
      return;
    }

    ui.typingArea.classList.remove("hidden");

    if (next === STATES.RECORDING) {
      ui.button.classList.add("state-recording");
      ui.icon.textContent = "⏺";
      ui.label.textContent = "Recording…";
      ui.status.textContent = "State: recording";
      ui.typedInput.focus();
      return;
    }

    ui.button.classList.add("state-ready");
    ui.icon.textContent = "➤";
    ui.label.textContent = "Send";
    ui.status.textContent = "State: ready";
  }

  async function initializeSession() {
    const formData = new FormData();
    formData.append("language", ui.language.value);

    setWorking(true);
    try {
      const response = await fetch("/initialize", { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        appendMessage("assistant", data.error || "Initialization failed.");
        return;
      }

      appendMessage("assistant", data.message || "Initialized. You can speak now.");
      setState(STATES.RECORDING);
    } finally {
      setWorking(false);
    }
  }

  async function sendTypedMessage() {
    const typedText = ui.typedInput.value.trim();
    if (!typedText) {
      setState(STATES.RECORDING);
      return;
    }

    setWorking(true);
    try {
      const response = await fetch("/upload-audio", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: typedText }),
      });

      const data = await response.json();
      if (!response.ok || !data.ok) {
        appendMessage("assistant", data.error || "Message failed.");
        setState(STATES.RECORDING);
        return;
      }

      appendMessage("user", typedText);
      appendMessage("assistant", data.reply || "No reply received.");

      ui.typedInput.value = "";
      setState(STATES.RECORDING);
    } finally {
      setWorking(false);
    }
  }

  ui.button.addEventListener("click", async () => {
    if (isWorking) return;

    if (state === STATES.INIT) {
      await initializeSession();
      return;
    }

    if (state === STATES.RECORDING) {
      const hasInput = ui.typedInput.value.trim().length > 0;
      if (hasInput) {
        setState(STATES.READY);
      }
      return;
    }

    await sendTypedMessage();
  });

  ui.typedInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && state === STATES.RECORDING) {
      event.preventDefault();
      if (ui.typedInput.value.trim().length > 0) {
        setState(STATES.READY);
      }
    }
  });

  setState(STATES.INIT);
})();
