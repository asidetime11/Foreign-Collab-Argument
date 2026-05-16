(function () {
  const list = document.getElementById("topic-list");
  const input = document.querySelector('input[name="ordered_topic_ids"]');
  const status = document.querySelector("[data-drag-status]");
  if (!list || !input) return;

  function items() {
    return Array.from(list.querySelectorAll("[data-topic-id]"));
  }

  function sync() {
    const currentItems = items();
    input.value = currentItems.map((item) => item.dataset.topicId).join(",");
    currentItems.forEach((item, index) => {
      item.classList.toggle("is-first", index === 0);
      item.classList.toggle("is-last", index === currentItems.length - 1);
      // Update topic number
      const numberElement = item.querySelector('.topic-number');
      if (numberElement) {
        numberElement.textContent = index + 1;
      }
    });
  }

  let dragged = null;
  let dragOverTarget = null;
  let autoScrollFrame = null;
  let autoScrollSpeed = 0;

  function setStatus(message) {
    if (status) status.textContent = message;
  }

  function clearDragOver() {
    if (dragOverTarget) {
      dragOverTarget.classList.remove("drag-over");
      dragOverTarget = null;
    }
  }

  function setDragOver(target) {
    if (dragOverTarget === target) return;
    clearDragOver();
    dragOverTarget = target;
    if (dragOverTarget) dragOverTarget.classList.add("drag-over");
  }

  function stopAutoScroll() {
    autoScrollSpeed = 0;
    if (autoScrollFrame) {
      window.cancelAnimationFrame(autoScrollFrame);
      autoScrollFrame = null;
    }
  }

  function autoScrollLoop() {
    if (!autoScrollSpeed) {
      autoScrollFrame = null;
      return;
    }
    window.scrollBy(0, autoScrollSpeed);
    autoScrollFrame = window.requestAnimationFrame(autoScrollLoop);
  }

  function updateAutoScroll(clientY) {
    const threshold = 110;
    const maxSpeed = 18;
    const topDistance = clientY;
    const bottomDistance = window.innerHeight - clientY;

    if (topDistance < threshold) {
      autoScrollSpeed = -Math.ceil(((threshold - topDistance) / threshold) * maxSpeed);
    } else if (bottomDistance < threshold) {
      autoScrollSpeed = Math.ceil(((threshold - bottomDistance) / threshold) * maxSpeed);
    } else {
      stopAutoScroll();
      return;
    }

    if (!autoScrollFrame) autoScrollFrame = window.requestAnimationFrame(autoScrollLoop);
  }

  function flashMoved(item) {
    item.classList.remove("just-moved");
    window.requestAnimationFrame(() => {
      item.classList.add("just-moved");
      window.setTimeout(() => item.classList.remove("just-moved"), 850);
    });
  }

  function finishDrag(message) {
    if (dragged) dragged.classList.remove("dragging");
    list.classList.remove("dragging-active");
    clearDragOver();
    stopAutoScroll();
    dragged = null;
    sync();
    setStatus(message || "排序已更新。");
  }

  list.addEventListener("dragstart", (event) => {
    dragged = event.target.closest("[data-topic-id]");
    if (!dragged) return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", dragged.dataset.topicId);
    dragged.classList.add("dragging");
    list.classList.add("dragging-active");
    setStatus("正在拖动，移到目标位置后松开即可。");
  });

  list.addEventListener("dragend", () => {
    if (dragged) {
      // Add bounce animation
      dragged.classList.add('drop-bounce');
      setTimeout(() => {
        if (dragged) dragged.classList.remove('drop-bounce');
      }, 300);
    }
    finishDrag("排序已更新。");
  });

  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest("[data-topic-id]");
    if (!target || !dragged || target === dragged) return;
    const rect = target.getBoundingClientRect();
    setDragOver(target);
    list.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? target : target.nextSibling);
    // Update numbers in real-time during drag
    sync();
  });

  list.addEventListener("dragleave", (event) => {
    if (!list.contains(event.relatedTarget)) clearDragOver();
  });

  document.addEventListener("dragover", (event) => {
    if (!dragged) return;
    event.preventDefault();
    updateAutoScroll(event.clientY);
  });

  document.addEventListener("drop", () => {
    if (!dragged) return;
    finishDrag("排序已更新。");
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
    flashMoved(item);
    const titleElement = item.querySelector(".topic-content h3");
    const title = titleElement ? titleElement.textContent : "话题";
    setStatus(`${title} 已移动到第 ${items().indexOf(item) + 1} 位。`);
  });

  sync();
})();
