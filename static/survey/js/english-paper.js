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
    let remaining = Number(root.dataset.remainingSeconds || 0);

  function render() {
    const hours = Math.floor(remaining / 3600);
    const minutes = Math.floor((remaining % 3600) / 60);
    const seconds = remaining % 60;
    value.textContent = `${twoDigits(hours)}:${twoDigits(minutes)}:${twoDigits(seconds)}`;
    root.classList.toggle("is-expired", remaining <= 0);
  }

  render();
  window.setInterval(() => {
    remaining = Math.max(remaining - 1, 0);
    render();
  }, 1000);
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
          saveButton.textContent = "暂时保存";
        }, 1200);
      } catch (error) {
        if (status) status.textContent = "暂存失败，请稍后再试。";
        saveButton.textContent = "暂时保存";
      } finally {
        saveButton.disabled = false;
      }
    });
  }
})();
