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
  };

  let state = STATES.INIT;
  let isWorking = false;
  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];

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

  function appendAudioPlayer(base64Audio, mimeType = "audio/mpeg") {
    if (!base64Audio) return;
    const wrapper = document.createElement("div");
    wrapper.className = "mb-3";
    const player = document.createElement("audio");
    player.controls = true;
    player.autoplay = true;
    player.src = `data:${mimeType};base64,${base64Audio}`;
    wrapper.appendChild(player);
    ui.chat.appendChild(wrapper);
    scrollChatToBottom();
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
      return;
    }

    if (next === STATES.IDLE) {
      ui.button.classList.add("state-idle");
      ui.icon.textContent = "🎤";
      ui.label.textContent = "Start Recording";
      ui.inputWrap.classList.add("hidden");
      ui.language.disabled = true;
      setStatus("Tap to start recording");
      return;
    }

    if (next === STATES.RECORDING) {
      ui.button.classList.add("state-recording");
      ui.icon.textContent = "■";
      ui.label.textContent = "Stop";
      ui.inputWrap.classList.add("hidden");
      setStatus("Recording...");
      return;
    }

    ui.button.classList.add("state-review");
    ui.icon.textContent = "➤";
    ui.label.textContent = "Send";
    ui.inputWrap.classList.remove("hidden");
    setStatus("Ready to edit");
  }

  function setWorking(working) {
    isWorking = working;
    ui.button.disabled = working;
    ui.button.classList.toggle("is-working", working);
  }

  async function initializeSession() {
    setWorking(true);
    try {
      const fd = new FormData();
      fd.append("language", ui.language.value);
      const response = await fetch("/initialize", { method: "POST", body: fd });
      if (!response.ok) {
        throw new Error("Initialize failed");
      }
      const data = await response.json();
      appendBubble("assistant", data.intro || "Initialized. You can start recording.");
      appendAudioPlayer(data.intro_audio, data.intro_audio_mime);
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
      ui.textInput.value = data.transcription || "";
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
      appendBubble("assistant", data.reply || "No reply returned.");
      appendAudioPlayer(data.reply_audio, data.reply_audio_mime);
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

  window.addEventListener("beforeunload", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    stopStreamTracks();
  });

  appendBubble("assistant", "Welcome — tap Initialize to start.");
  setState(STATES.INIT);
})();
