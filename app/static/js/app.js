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
    inputWrap: document.getElementById("inputWrap"),
    textInput: document.getElementById("textInput"),
  };

  let state = STATES.INIT;
  let isWorking = false;

  function scrollChatToBottom() {
    ui.chat.scrollTop = ui.chat.scrollHeight;
  }

  function appendBubble(role, content) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role === "user" ? "chat-user" : "chat-assistant"}`;
    bubble.textContent = content;
    ui.chat.appendChild(bubble);
    scrollChatToBottom();
  }

  function setWorking(working) {
    isWorking = working;
    ui.button.disabled = working;
    ui.button.classList.toggle("is-working", working);
    if (working) {
      ui.label.textContent = "Working…";
      ui.icon.textContent = "⏳";
    } else {
      setState(state);
    }
  }

  function setState(next) {
    state = next;
    ui.button.classList.remove("state-init", "state-recording", "state-ready");

    if (next === STATES.INIT) {
      ui.button.classList.add("state-init");
      ui.icon.textContent = "⚙";
      ui.label.textContent = "Initialize";
      ui.status.textContent = "State: init";
      ui.inputWrap.classList.add("hidden");
      return;
    }

    ui.inputWrap.classList.remove("hidden");

    if (next === STATES.RECORDING) {
      ui.button.classList.add("state-recording");
      ui.icon.textContent = "●";
      ui.label.textContent = "Recording…";
      ui.status.textContent = "State: recording (ready for input)";
    } else {
      ui.button.classList.add("state-ready");
      ui.icon.textContent = "➤";
      ui.label.textContent = "Send";
      ui.status.textContent = "State: ready";
    }
  }

  async function initializeSession() {
    setWorking(true);
    try {
      const fd = new FormData();
      fd.append("language", ui.language.value);

      const response = await fetch("/initialize", { method: "POST", body: fd });
      if (!response.ok) throw new Error("Initialize failed");
      const data = await response.json();

      appendBubble("assistant", data.message || "Initialized. You can speak now.");
      setState(STATES.RECORDING);
    } catch (error) {
      appendBubble("assistant", "Initialization failed. Please try again.");
      setState(STATES.INIT);
    } finally {
      setWorking(false);
    }
  }

  async function sendTextStub() {
    const text = ui.textInput.value.trim();
    if (!text) {
      setState(STATES.RECORDING);
      return;
    }

    setWorking(true);
    try {
      const response = await fetch("/upload-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) throw new Error("Send failed");
      const data = await response.json();

      appendBubble("user", text);
      appendBubble("assistant", data.reply || "No reply returned.");
      ui.textInput.value = "";
      setState(STATES.RECORDING);
    } catch (error) {
      appendBubble("assistant", "Sorry, something went wrong while sending.");
      setState(STATES.READY);
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
      if (ui.textInput.value.trim()) {
        setState(STATES.READY);
      }
      return;
    }

    await sendTextStub();
  });

  appendBubble("assistant", "Welcome — tap Initialize to start.");
  setState(STATES.INIT);
})();
