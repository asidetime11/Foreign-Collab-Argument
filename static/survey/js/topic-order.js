(function () {
  const list = document.getElementById("topic-list");
  const input = document.querySelector('input[name="ordered_topic_ids"]');
  if (!list || !input) return;

  function sync() {
    input.value = Array.from(list.querySelectorAll("[data-topic-id]")).map((item) => item.dataset.topicId).join(",");
  }

  let dragged = null;
  list.addEventListener("dragstart", (event) => {
    dragged = event.target.closest("[data-topic-id]");
  });
  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest("[data-topic-id]");
    if (!target || target === dragged) return;
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
