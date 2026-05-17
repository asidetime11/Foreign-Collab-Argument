(function () {
  const panel = document.querySelector(".chat[data-round-id]");
  const form = document.getElementById("chat-form");
  const log = document.getElementById("chat-log");
  if (!panel || !form || !log) return;

  const finishForm = document.querySelector(".chat-finish");
  const countdown = document.querySelector("[data-countdown]");
  const status = document.querySelector("[data-chat-status]");
  let remaining = Number(panel.dataset.remainingSeconds || Number(panel.dataset.minutes || 0) * 60);

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  function format(seconds) {
    const minutes = Math.floor(seconds / 60);
    const rest = String(seconds % 60).padStart(2, "0");
    return `${minutes}:${rest}`;
  }

  function setStatus(text, visible) {
    if (!status) return;
    status.textContent = text;
    status.hidden = !visible;
  }

  function escapeHtml(text) {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function inlineMarkdown(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  }

  function renderMarkdown(text) {
    const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
    const blocks = [];
    let paragraph = [];
    let list = null;

    function closeParagraph() {
      if (!paragraph.length) return;
      blocks.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    }

    function closeList() {
      if (!list) return;
      blocks.push(`<${list.type}>${list.items.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</${list.type}>`);
      list = null;
    }

    lines.forEach((line) => {
      const trimmed = line.trim();
      const heading = trimmed.match(/^#{1,6}\s+(.+)$/);
      const unordered = trimmed.match(/^[-*]\s+(.+)$/);
      const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);

      if (!trimmed) {
        closeParagraph();
        closeList();
        return;
      }
      if (heading) {
        closeParagraph();
        closeList();
        blocks.push(`<p class="markdown-heading">${inlineMarkdown(heading[1])}</p>`);
        return;
      }
      if (unordered || ordered) {
        closeParagraph();
        const type = unordered ? "ul" : "ol";
        if (!list || list.type !== type) {
          closeList();
          list = { type, items: [] };
        }
        list.items.push((unordered || ordered)[1]);
        return;
      }
      closeList();
      paragraph.push(trimmed);
    });

    closeParagraph();
    closeList();
    return blocks.join("") || "";
  }

  function applyMarkdown(node, text) {
    node.dataset.markdownSource = text;
    node.innerHTML = renderMarkdown(text);
  }

  function bubble(text, role, markdown) {
    const row = document.createElement("article");
    row.className = `chat-message ${role}`;
    row.dataset.chatRole = role;

    const speaker = document.createElement("span");
    speaker.className = "chat-speaker";
    speaker.textContent = role === "participant" ? "你" : "AI";

    const node = document.createElement("div");
    node.className = `bubble ${role}`;
    if (markdown) {
      applyMarkdown(node, text);
    } else {
      node.textContent = text;
    }

    row.appendChild(speaker);
    row.appendChild(node);
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return node;
  }

  function createTextRevealer(node) {
    const queue = [];
    let timer = null;
    let pending = "";
    let rawText = node.dataset.markdownSource || node.textContent || "";

    function appendText(text) {
      rawText += text;
      if (node.hasAttribute("data-markdown-source")) {
        applyMarkdown(node, rawText);
      } else {
        node.textContent = rawText;
      }
    }

    function revealNext() {
      if (!pending && queue.length) pending = queue.shift();
      if (pending) {
        const step = /[\u4e00-\u9fa5]/.test(pending[0]) ? 2 : 4;
        appendText(pending.slice(0, step));
        pending = pending.slice(step);
        log.scrollTop = log.scrollHeight;
      }
      if (!pending && !queue.length && timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function start() {
      if (!timer) timer = window.setInterval(revealNext, 45);
    }

    return {
      push(text) {
        if (!text) return;
        queue.push(text);
        start();
      },
      finish() {
        return new Promise((resolve) => {
          const waiter = window.setInterval(() => {
            if (!timer && !pending && !queue.length) {
              window.clearInterval(waiter);
              resolve();
            }
          }, 45);
          start();
        });
      }
    };
  }

  log.querySelectorAll("[data-markdown-source]").forEach((node) => {
    applyMarkdown(node, node.textContent);
  });
  log.scrollTop = log.scrollHeight;

  if (finishForm && finishForm.hasAttribute("data-confirm-finish")) {
    finishForm.addEventListener("submit", function (event) {
      const confirmed = window.confirm("确认完成这轮对话吗？提交后不能继续本轮对话。");
      if (!confirmed) {
        event.preventDefault();
      }
    });
  }

  function handleServerEvent(block, revealer, assistant) {
    if (!block.trim()) return false;
    const lines = block.split("\n");
    const event = lines.find((line) => line.startsWith("event: "));
    const dataLines = lines.filter((line) => line.startsWith("data: "));
    const payload = dataLines.map((line) => line.slice(6)).join("\n");

    if (event && event.includes("event: error")) {
      assistant.classList.add("error");
      revealer.push(payload || "暂时没有收到稳定回复，请稍后再试一次。");
      return true;
    }
    if (event && event.includes("event: done")) return true;
    if (payload && payload !== "ok") revealer.push(payload);
    return false;
  }

  if (countdown) {
    countdown.textContent = format(remaining);
    const timer = window.setInterval(() => {
      remaining -= 1;
      countdown.textContent = format(Math.max(remaining, 0));
      if (remaining <= 0) {
        window.clearInterval(timer);
        if (finishForm) finishForm.submit();
      }
    }, 1000);
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const input = form.querySelector("input[name=message]");
    const send = form.querySelector('button[type="submit"]');
    const text = input.value.trim();
    if (!text) return;
    bubble(text, "participant");
    input.value = "";
    input.disabled = true;
    if (send) send.disabled = true;
    const assistant = bubble("", "assistant", true);
    const revealer = createTextRevealer(assistant);
    setStatus("正在整理回复...", true);

    const data = new FormData();
    data.append("message", text);
    try {
      const response = await fetch("/ai/chat/" + panel.dataset.roundId + "/", {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: data
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        blocks.forEach((block) => handleServerEvent(block, revealer, assistant));
        setStatus("AI 正在回复...", true);
      }
      if (buffer) handleServerEvent(buffer, revealer, assistant);
      await revealer.finish();
    } catch (error) {
      assistant.classList.add("error");
      revealer.push("暂时没有收到稳定回复，请稍后再试一次。");
      await revealer.finish();
    } finally {
      setStatus("", false);
      input.disabled = false;
      if (send) send.disabled = false;
      input.focus();
    }
  });
})();
