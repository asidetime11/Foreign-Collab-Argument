(function () {
  function csrfToken() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
  }

  function send(eventType, metadata) {
    if (!document.body || !csrfToken()) return;
    fetch("/survey/quality-event/", {
      method: "POST",
      keepalive: true,
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify({ event_type: eventType, metadata: metadata || {} })
    });
  }

  ["copy", "paste", "cut", "contextmenu"].forEach(function (eventName) {
    document.addEventListener(eventName, function (event) {
      event.preventDefault();
      send(eventName, { path: location.pathname });
    });
  });

  document.addEventListener("keydown", function (event) {
    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && ["c", "v", "x"].includes(key)) {
      event.preventDefault();
      send("shortcut", { key: key, path: location.pathname });
    }
  });
})();
