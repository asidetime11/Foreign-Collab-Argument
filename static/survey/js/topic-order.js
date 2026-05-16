(function () {
  const list = document.getElementById("topic-list");
  const input = document.querySelector('input[name="ordered_topic_ids"]');
  if (!list || !input) return;

  function items() {
    return Array.from(list.querySelectorAll("[data-topic-id]"));
  }

  function sync() {
    const currentItems = items();
    input.value = currentItems.map((item) => item.dataset.topicId).join(",");
    currentItems.forEach((item, index) => {
      const rank = item.querySelector(".topic-rank");
      if (rank) rank.textContent = `第 ${index + 1} 位`;
      item.classList.toggle("is-first", index === 0);
      item.classList.toggle("is-last", index === currentItems.length - 1);
    });
  }

  let dragged = null;

  list.addEventListener("dragstart", (event) => {
    dragged = event.target.closest("[data-topic-id]");
    if (dragged) dragged.classList.add("dragging");
  });

  list.addEventListener("dragend", () => {
    if (dragged) dragged.classList.remove("dragging");
    dragged = null;
    sync();
  });

  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest("[data-topic-id]");
    if (!target || !dragged || target === dragged) return;
    const rect = target.getBoundingClientRect();
    list.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? target : target.nextSibling);
    sync();
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-move]");
    if (!button) return;
    const item = button.closest("[data-topic-id]");
    if (button.dataset.move === "up" && item.previousElementSibling) {
      list.insertBefore(item, item.previousElementSibling);
    }
    if (button.dataset.move === "down" && item.nextElementSibling) {
      list.insertBefore(item.nextElementSibling, item);
    }
    sync();
  });

  sync();
})();
