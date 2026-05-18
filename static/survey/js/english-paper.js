(function () {
  const root = document.querySelector("[data-paper-countdown]");
  const saveButton = document.querySelector("[data-paper-save-draft]");
  const textarea = document.querySelector('textarea[name="paper_text"]');
  const status = document.querySelector("[data-paper-draft-status]");

  function twoDigits(number) {
    return String(Math.max(0, number)).padStart(2, "0");
  }

  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  if (root) {
    const value = root.querySelector("[data-countdown-value]");
    const initialRemaining = Math.max(Number(root.dataset.remainingSeconds || 0), 0);
    const deadlineAt = Number(root.dataset.deadlineAt || 0) || Date.now() + initialRemaining * 1000;
    let remaining = initialRemaining;

    function updateRemaining() {
      remaining = Math.max(Math.ceil((deadlineAt - Date.now()) / 1000), 0);
      root.dataset.remainingSeconds = String(remaining);
    }

    function render() {
      updateRemaining();
      const hours = Math.floor(remaining / 3600);
      const minutes = Math.floor((remaining % 3600) / 60);
      const seconds = remaining % 60;
      value.textContent = `${twoDigits(hours)}:${twoDigits(minutes)}:${twoDigits(seconds)}`;
      root.classList.toggle("is-expired", remaining <= 0);
    }

    render();
    window.setInterval(render, 1000);
    window.addEventListener("pageshow", render);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) render();
    });
  }

  if (saveButton && textarea) {
    saveButton.addEventListener("click", async function () {
      saveButton.disabled = true;
      saveButton.textContent = "正在保存...";
      const data = new FormData();
      data.append("paper_text", textarea.value);
      try {
        const response = await fetch(saveButton.dataset.draftUrl, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken() },
          body: data,
        });
        if (!response.ok) throw new Error(await response.text());
        const payload = await response.json();
        if (status) status.textContent = `已暂存 ${payload.saved_at || ""}`.trim();
        saveButton.textContent = "已暂存";
        window.setTimeout(() => {
          saveButton.textContent = "暂存想法";
        }, 1200);
      } catch (error) {
        if (status) status.textContent = "暂存失败，请稍后再试。";
        saveButton.textContent = "暂存想法";
      } finally {
        saveButton.disabled = false;
      }
    });
  }
})();
