(function () {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";

  function record(eventType, metadata) {
    if (!token) return;
    fetch("/survey/quality-event/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ event_type: eventType, metadata }),
      keepalive: true
    }).catch(() => {});
  }

  function isEditableTarget(target) {
    if (!target) return false;
    const editable = target.closest?.("input, textarea, select, [contenteditable='true']");
    if (!editable) return false;
    if (editable.matches?.("input, textarea")) return !editable.readOnly && !editable.disabled;
    if (editable.matches?.("select")) return !editable.disabled;
    return true;
  }

  function blockPageTransfer(event) {
    event.preventDefault();
    record(event.type === "drop" ? "paste" : event.type, { path: window.location.pathname, source: event.type });
  }

  document.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    record("contextmenu", { path: window.location.pathname });
  });

  ["paste", "drop", "copy", "cut"].forEach((eventName) => {
    document.addEventListener(eventName, blockPageTransfer);
  });

  document.addEventListener("keydown", (event) => {
    if (!isEditableTarget(event.target)) {
      const isBackspaceNavigation = event.key === "Backspace";
      const isAltBack = event.key === "ArrowLeft" && event.altKey;
      const isBrowserBack = event.key === "BrowserBack";
      if (isBackspaceNavigation || isAltBack || isBrowserBack) {
        event.preventDefault();
        record("shortcut", { key: event.key, path: window.location.pathname, source: "browser-back" });
        return;
      }
    }

    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && ["c", "v", "x"].includes(key)) {
      event.preventDefault();
      record("shortcut", { key, path: window.location.pathname });
    }
  });
})();
