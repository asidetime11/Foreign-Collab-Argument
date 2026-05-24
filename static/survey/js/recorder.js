(function () {
  const buttons = Array.from(document.querySelectorAll("[data-recorder]"));
  if (!buttons.length) return;

  function markUnsupported() {
    buttons.forEach((button) => {
      button.disabled = true;
      button.textContent = "浏览器不支持录音";
      button.removeAttribute("title");
      report("unsupported", "当前浏览器不支持录音或语音转写。");
    });
  }

  if (!navigator.mediaDevices || !window.MediaRecorder) {
    markUnsupported();
    return;
  }

  function preferredMimeType() {
    const candidates = ["audio/webm", "audio/mp4", "audio/ogg"];
    for (const type of candidates) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return "";
  }

  const mimeType = preferredMimeType();

  let recorder = null;
  let activeButton = null;
  let chunks = [];
  let stream = null;

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  function report(event, detail) {
    const data = new FormData();
    data.append("event", event);
    data.append("detail", detail || "");
    fetch("/ai/transcribe-debug/", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: data,
    }).catch(() => {});
  }

  report("script-loaded", `buttons=${buttons.length} url=${window.location.pathname}`);

  function targetFor(button) {
    const selector = button.getAttribute("data-recorder-target") || 'textarea[name="final_text"]';
    return document.querySelector(selector);
  }

  function setHiddenValue(name, value) {
    const node = document.querySelector(`input[name=${name}]`);
    if (node) node.value = value;
  }

  function appendTranscription(text, target) {
    if (!target || !text) return;
    const current = target.value.trimEnd();
    const separator = current && !/\s$/.test(current) ? " " : "";
    target.value = current ? `${current}${separator}${text}` : text;
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.focus();
  }

  function resetButton(button) {
    button.disabled = false;
    button.textContent = "语音输入";
    button.removeAttribute("title");
    button.classList.remove("is-recording", "is-working");
  }

  function stopStream() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
  }

  async function uploadRecording(button, target) {
    button.textContent = "正在转写...";
    button.classList.remove("is-recording");
    button.classList.add("is-working");
    button.disabled = true;
    const bytes = chunks.reduce((total, chunk) => total + chunk.size, 0);
    report("upload-start", `chunks=${chunks.length} bytes=${bytes} mime=${mimeType}`);

    const ext = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
    const data = new FormData();
    data.append("audio", new Blob(chunks, { type: mimeType || "audio/webm" }), `recording.${ext}`);
    const response = await fetch("/ai/transcribe/", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: data,
    });
    if (!response.ok) {
      const raw = await response.text();
      try {
        const payload = JSON.parse(raw);
        const details = [
          payload.error,
          payload.detail && payload.detail !== payload.error ? `详细错误：${payload.detail}` : "",
          payload.model ? `模型：${payload.model}` : "",
        ].filter(Boolean);
        throw new Error(details.join("\n") || raw);
      } catch (parseError) {
        if (parseError instanceof SyntaxError) throw new Error(raw);
        throw parseError;
      }
    }
    const payload = await response.json();
    appendTranscription(payload.text, target);
    setHiddenValue("input_method", "speech_to_text");
    setHiddenValue("transcribe_model", payload.model || "");
    report("upload-success", `chars=${(payload.text || "").length} model=${payload.model || ""}`);
  }

  buttons.forEach((button) => {
    button.addEventListener("click", async function () {
      report("click", `state=${recorder ? recorder.state : "idle"}`);
      if (recorder && recorder.state === "recording" && activeButton === button) {
        report("stop-requested", "active button clicked");
        recorder.stop();
        return;
      }
      if (recorder && recorder.state === "recording") {
        report("stop-requested", "another recorder was active");
        recorder.stop();
        return;
      }

      const target = targetFor(button);
      if (!target) {
        report("target-missing", button.getAttribute("data-recorder-target") || "");
        return;
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        report("microphone-opened", `tracks=${stream.getTracks().length}`);
        const recorderOptions = mimeType ? { mimeType } : {};
        recorder = new MediaRecorder(stream, recorderOptions);
        activeButton = button;
        chunks = [];

        recorder.addEventListener("dataavailable", (event) => {
          if (event.data && event.data.size) {
            chunks.push(event.data);
            report("dataavailable", `size=${event.data.size} chunks=${chunks.length}`);
          }
        });
        recorder.addEventListener("stop", async () => {
          report("recording-stopped", `chunks=${chunks.length}`);
          try {
            await uploadRecording(button, target);
          } catch (error) {
            const message = error.message || "语音转写失败";
            console.error(`[recorder] 语音转写失败：${message}`);
            report("upload-error", message);
            button.textContent = "转写失败";
            button.removeAttribute("title");
            window.setTimeout(() => resetButton(button), 1400);
            return;
          } finally {
            stopStream();
            recorder = null;
            activeButton = null;
          }
          resetButton(button);
        });

        recorder.start();
        report("recording-started", recorder.mimeType || "unknown mime");
        button.textContent = "停止录音";
        button.classList.add("is-recording");
      } catch (error) {
        const message = error.message || "无法录音";
        report("microphone-error", message);
        button.textContent = "无法录音";
        window.setTimeout(() => resetButton(button), 1400);
      }
    });
  });
})();
