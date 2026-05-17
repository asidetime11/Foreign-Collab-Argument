(function () {
  const buttons = Array.from(document.querySelectorAll("[data-recorder]"));
  if (!buttons.length || !navigator.mediaDevices || !window.MediaRecorder) return;

  let recorder = null;
  let activeButton = null;
  let chunks = [];
  let stream = null;

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

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
    target.value = current ? `${current}\n${text}` : text;
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.focus();
  }

  function resetButton(button) {
    button.disabled = false;
    button.textContent = "语音输入";
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

    const data = new FormData();
    data.append("audio", new Blob(chunks, { type: "audio/webm" }), "recording.webm");
    const response = await fetch("/ai/transcribe/", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: data,
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const payload = await response.json();
    appendTranscription(payload.text, target);
    setHiddenValue("input_method", "speech_to_text");
    setHiddenValue("transcribe_model", payload.model || "");
  }

  buttons.forEach((button) => {
    button.addEventListener("click", async function () {
      if (recorder && recorder.state === "recording" && activeButton === button) {
        recorder.stop();
        return;
      }

      const target = targetFor(button);
      if (!target) return;

      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream);
        activeButton = button;
        chunks = [];

        recorder.addEventListener("dataavailable", (event) => {
          if (event.data && event.data.size) chunks.push(event.data);
        });
        recorder.addEventListener("stop", async () => {
          try {
            await uploadRecording(button, target);
          } catch (error) {
            button.textContent = "转写失败";
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
        button.textContent = "停止录音";
        button.classList.add("is-recording");
      } catch (error) {
        button.textContent = "无法录音";
        window.setTimeout(() => resetButton(button), 1400);
      }
    });
  });
})();
