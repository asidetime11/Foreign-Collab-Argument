(function () {
  const panel = document.querySelector(".chat[data-round-id]");
  const form = document.getElementById("chat-form");
  const log = document.getElementById("chat-log");
  if (!panel || !form || !log) return;

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  function bubble(text, role) {
    const node = document.createElement("div");
    node.className = "bubble " + role;
    node.textContent = text;
    log.appendChild(node);
    return node;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const input = form.querySelector("input[name=message]");
    const text = input.value.trim();
    if (!text) return;
    bubble(text, "participant");
    input.value = "";
    input.disabled = true;
    const assistant = bubble("", "assistant");
    const data = new FormData();
    data.append("message", text);
    const response = await fetch("/ai/chat/" + panel.dataset.roundId + "/", { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const result = await reader.read();
      if (result.done) break;
      decoder.decode(result.value).split("\n").forEach(function (line) {
        if (line.startsWith("data: ") && line !== "data: ok") assistant.textContent += line.slice(6);
      });
    }
    input.disabled = false;
    input.focus();
  });
})();
