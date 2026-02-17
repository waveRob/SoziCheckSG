(() => {
  const STATES = {
    INIT: "init",
    IDLE: "idle",
    RECORDING: "recording",
    REVIEW: "review",
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
    chipsWrap: document.getElementById("chipsWrap"),
    chipsContainer: document.getElementById("chipsContainer"),
  };

  let state = STATES.INIT;
  let isWorking = false;
  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];
  let draftText = "";
  let lastAssistantText = "";

  function scrollChatToBottom() {
    ui.chat.scrollTop = ui.chat.scrollHeight;
  }

  function appendBubble(role, content) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble-enter ${role === "user" ? "chat-user" : "chat-assistant"}`;
    bubble.textContent = content;
    ui.chat.appendChild(bubble);
    if (role === "assistant") {
      lastAssistantText = content || "";
    }
    scrollChatToBottom();
    return bubble;
  }

  function appendAudioPlayer(base64Audio, mimeType = "audio/mpeg", bubble = null) {
    if (!base64Audio) return;

    const targetBubble = bubble || appendBubble("assistant", "");
    const audio = document.createElement("audio");
    audio.src = `data:${mimeType};base64,${base64Audio}`;
    audio.preload = "none";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "audio-toggle";
    toggle.textContent = "🔊";
    toggle.setAttribute("aria-label", "Play audio response");

    const setMuted = () => {
      toggle.textContent = "🔊";
      toggle.setAttribute("aria-label", "Play audio response");
    };

    const setPlaying = () => {
      toggle.textContent = "🔇";
      toggle.setAttribute("aria-label", "Stop audio response");
    };

    toggle.addEventListener("click", async () => {
      if (audio.paused) {
        try {
          await audio.play();
          setPlaying();
        } catch (error) {
          setMuted();
        }
      } else {
        audio.pause();
        audio.currentTime = 0;
        setMuted();
      }
    });

    audio.addEventListener("pause", setMuted);
    audio.addEventListener("ended", setMuted);
    audio.addEventListener("play", setPlaying);

    targetBubble.appendChild(toggle);
    targetBubble.appendChild(audio);

    audio.play().catch(() => {
      setMuted();
    });

    scrollChatToBottom();
  }

  function detectQuickReplies(text) {
    if (!text) return [];
    const normalized = text.toLowerCase();
    const options = [];

    if (/\b(yes|no|ja|nein)\b/.test(normalized) || /\?/.test(normalized) || /bitte antworten sie/.test(normalized)) {
      options.push("Ja", "Nein");
    }

    const thresholdMatch = text.match(/([<>]=?|über|unter|mehr als|weniger als)\s*([\d'.,]+\s*(?:chf|eur|€|fr|franken)?)/gi);
    if (thresholdMatch && thresholdMatch.length >= 1) {
      const cleaned = thresholdMatch.map((item) => item.trim());
      cleaned.slice(0, 2).forEach((item) => options.push(item));
    }

    if (!options.length) {
      const eitherOr = text.match(/\b([^?.!\n]{1,35})\s+(?:oder|or)\s+([^?.!\n]{1,35})\b/i);
      if (eitherOr) {
        options.push(eitherOr[1].trim(), eitherOr[2].trim());
      }
    }

    if (!options.length && /\?/.test(normalized)) {
      options.push("Ja", "Nein");
    }

    return [...new Set(options)].slice(0, 4);
  }

  function paintQuickReplyChips(quickReplies) {
    if (state !== STATES.IDLE || !quickReplies.length) {
      ui.chipsWrap.classList.add("hidden");
      ui.chipsContainer.innerHTML = "";
      return;
    }

    ui.chipsContainer.innerHTML = "";
    quickReplies.forEach((value) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "quick-chip";
      chip.textContent = value;
      chip.addEventListener("click", () => {
        draftText = value;
        ui.textInput.value = draftText;
        setState(STATES.REVIEW);
      });
      ui.chipsContainer.appendChild(chip);
    });

    ui.chipsWrap.classList.remove("hidden");
  }

  async function fetchSmartQuickReplies(text) {
    if (!text || !text.trim()) return [];

    try {
      const response = await fetch("/quick-replies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        return [];
      }

      const data = await response.json();
      if (!Array.isArray(data.quick_replies)) {
        return [];
      }

      return data.quick_replies
        .filter((item) => typeof item === "string")
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
        .slice(0, 4);
    } catch (error) {
      return [];
    }
  }

  async function renderQuickReplyChips() {
    if (state !== STATES.IDLE) {
      paintQuickReplyChips([]);
      return;
    }

    const snapshotText = lastAssistantText;
    const smartReplies = await fetchSmartQuickReplies(snapshotText);
    if (snapshotText !== lastAssistantText || state !== STATES.IDLE) {
      return;
    }

    const quickReplies = smartReplies.length ? smartReplies : detectQuickReplies(snapshotText);
    paintQuickReplyChips(quickReplies);
  }

  function setStatus(text) {
    ui.status.textContent = text;
  }

  function setState(next) {
    state = next;
    ui.button.classList.remove("state-init", "state-idle", "state-recording", "state-review");

    if (next === STATES.INIT) {
      ui.button.classList.add("state-init");
      ui.icon.textContent = "⚙";
      ui.label.textContent = "Initialize";
      ui.inputWrap.classList.add("hidden");
      ui.language.disabled = false;
      setStatus("Ready to initialize");
      renderQuickReplyChips();
      return;
    }

    if (next === STATES.IDLE) {
      ui.button.classList.add("state-idle");
      ui.icon.textContent = "🎤";
      ui.label.textContent = "Start Recording";
      ui.inputWrap.classList.add("hidden");
      ui.language.disabled = true;
      setStatus("Ready to record");
      renderQuickReplyChips();
      return;
    }

    if (next === STATES.RECORDING) {
      ui.button.classList.add("state-recording");
      ui.icon.textContent = "■";
      ui.label.textContent = "Stop";
      ui.inputWrap.classList.add("hidden");
      setStatus("Recording...");
      renderQuickReplyChips();
      return;
    }

    ui.button.classList.add("state-review");
    ui.icon.textContent = "➤";
    ui.label.textContent = "Send";
    ui.inputWrap.classList.remove("hidden");
    setStatus("Ready to edit");
    renderQuickReplyChips();
  }

  function setWorking(working) {
    isWorking = working;
    ui.button.disabled = working;
    ui.button.classList.toggle("is-working", working);
  }

  async function initializeSession() {
    setWorking(true);
    setStatus("Initializing...");
    try {
      const fd = new FormData();
      fd.append("language", ui.language.value);
      const response = await fetch("/initialize", { method: "POST", body: fd });
      if (!response.ok) {
        throw new Error("Initialize failed");
      }
      const data = await response.json();
      const bubble = appendBubble("assistant", data.intro || "Initialized. You can start recording.");
      appendAudioPlayer(data.intro_audio, data.intro_audio_mime, bubble);
      setState(STATES.IDLE);
    } catch (error) {
      appendBubble("assistant", "Initialization failed. Please try again.");
      setState(STATES.INIT);
    } finally {
      setWorking(false);
    }
  }

  async function ensureMicSupportAndPermission() {
    if (!window.MediaRecorder || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("Audio recording is not supported in this browser.");
    }

    if (!mediaStream) {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }

    return mediaStream;
  }

  async function startRecording() {
    setWorking(true);
    try {
      const stream = await ensureMicSupportAndPermission();
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      });

      mediaRecorder.start();
      setState(STATES.RECORDING);
    } catch (error) {
      appendBubble("assistant", error.message || "Microphone permission was denied.");
      setStatus("Microphone unavailable");
      setState(STATES.IDLE);
    } finally {
      setWorking(false);
    }
  }

  function stopStreamTracks() {
    if (!mediaStream) return;
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  async function stopRecordingAndTranscribe() {
    if (!mediaRecorder || mediaRecorder.state !== "recording") {
      return;
    }

    setWorking(true);
    setStatus("Transcribing...");

    try {
      const audioBlob = await new Promise((resolve, reject) => {
        mediaRecorder.addEventListener(
          "stop",
          () => {
            if (!audioChunks.length) {
              reject(new Error("No audio captured."));
              return;
            }
            resolve(new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" }));
          },
          { once: true },
        );

        mediaRecorder.addEventListener(
          "error",
          () => reject(new Error("Recording failed.")),
          { once: true },
        );

        mediaRecorder.stop();
      });

      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      const response = await fetch("/upload-audio", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Transcription failed.");
      }

      const data = await response.json();
      draftText = data.transcription || "";
      ui.textInput.value = draftText;
      setState(STATES.REVIEW);
    } catch (error) {
      appendBubble("assistant", error.message || "Could not transcribe audio.");
      setState(STATES.IDLE);
    } finally {
      audioChunks = [];
      mediaRecorder = null;
      stopStreamTracks();
      setWorking(false);
    }
  }

  async function sendEditedMessage() {
    const text = ui.textInput.value.trim();
    if (!text) {
      appendBubble("assistant", "Please enter text before sending.");
      return;
    }

    setWorking(true);
    setStatus("Sending...");

    try {
      const response = await fetch("/send-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error("Send failed.");
      }

      const data = await response.json();
      appendBubble("user", text);
      const bubble = appendBubble("assistant", data.reply || "No reply returned.");
      appendAudioPlayer(data.reply_audio, data.reply_audio_mime, bubble);
      draftText = "";
      ui.textInput.value = "";
      setState(STATES.IDLE);
    } catch (error) {
      appendBubble("assistant", error.message || "Something went wrong while sending.");
      setState(STATES.REVIEW);
    } finally {
      setWorking(false);
    }
  }

  ui.button.addEventListener("click", async () => {
    if (isWorking) {
      return;
    }

    if (state === STATES.INIT) {
      await initializeSession();
      return;
    }

    if (state === STATES.IDLE) {
      await startRecording();
      return;
    }

    if (state === STATES.RECORDING) {
      await stopRecordingAndTranscribe();
      return;
    }

    await sendEditedMessage();
  });

  ui.textInput.addEventListener("input", () => {
    draftText = ui.textInput.value;
  });

  window.addEventListener("beforeunload", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    stopStreamTracks();
  });

  appendBubble("assistant", "Welcome — tap Initialize to start.");
  setState(STATES.INIT);
})();
