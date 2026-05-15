(function () {
  const button = document.querySelector("[data-recorder]");
  if (!button || !navigator.mediaDevices) return;
  const textarea = document.querySelector("textarea[name=final_text]");
  const method = document.querySelector("input[name=input_method]");
  const model = document.querySelector("input[name=transcribe_model]");
  let recorder;
  let chunks = [];

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  button.addEventListener("click", async function () {
    if (recorder && recorder.state === "recording") {
      recorder.stop();
      button.textContent = "录音转文字";
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    chunks = [];
    recorder.ondataavailable = (event) => chunks.push(event.data);
    recorder.onstop = async function () {
      const data = new FormData();
      data.append("audio", new Blob(chunks, { type: "audio/webm" }), "recording.webm");
      const response = await fetch("/ai/transcribe/", { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data });
      if (response.ok) {
        const payload = await response.json();
        textarea.value = payload.text;
        method.value = "speech_to_text";
        model.value = payload.model;
      }
    };
    recorder.start();
    button.textContent = "停止录音";
  });
})();
