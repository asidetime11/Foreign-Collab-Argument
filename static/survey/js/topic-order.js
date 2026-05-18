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
      const rank = item.querySelector("[data-topic-rank]");
      if (rank) rank.textContent = String(index + 1);
    });
  }

  let dragged = null;
  let activeDragElement = null;
  let activePointerId = null;
  let dragOverTarget = null;
  let autoScrollFrame = null;
  let autoScrollSpeed = 0;
  let pendingClientY = null;
  let moveFrame = null;

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

  function animateReorder(callback) {
    const before = new Map(items().map((item) => [item, item.getBoundingClientRect()]));
    callback();
    items().forEach((item) => {
      const start = before.get(item);
      if (!start) return;
      const end = item.getBoundingClientRect();
      const deltaY = start.top - end.top;
      if (!deltaY) return;
      item.style.transition = "none";
      item.style.transform = `translateY(${deltaY}px)`;
      item.getBoundingClientRect();
      item.style.transition = "";
      item.style.transform = "";
    });
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

  function insertBeforeForY(clientY) {
    return items().find((item) => {
      if (item === dragged) return false;
      const rect = item.getBoundingClientRect();
      return clientY < rect.top + rect.height / 2;
    }) || null;
  }

  function moveDragged(clientY) {
    if (!dragged) return;
    const beforeNode = insertBeforeForY(clientY);
    const visibleTarget = beforeNode || items().filter((item) => item !== dragged).at(-1) || null;
    setDragOver(visibleTarget);

    if (beforeNode === dragged || beforeNode === dragged.nextElementSibling) return;
    if (!beforeNode && dragged === items().at(-1)) return;

    animateReorder(() => {
      list.insertBefore(dragged, beforeNode);
    });
    sync();
  }

  function scheduleMove(clientY) {
    pendingClientY = clientY;
    if (moveFrame) return;
    moveFrame = window.requestAnimationFrame(() => {
      moveFrame = null;
      moveDragged(pendingClientY);
    });
  }

  function flashMoved(item) {
    item.classList.remove("just-moved");
    window.requestAnimationFrame(() => {
      item.classList.add("just-moved");
      window.setTimeout(() => item.classList.remove("just-moved"), 850);
    });
  }

  function beginDrag(event) {
    if (event.target.closest("button, a, input, textarea, select")) return;
    const item = event.target.closest("[data-topic-id]");
    if (!item) return;
    event.preventDefault();

    dragged = item;
    activeDragElement = item;
    activePointerId = event.pointerId;
    activeDragElement.setPointerCapture(activePointerId);
    dragged.classList.add("dragging");
    list.classList.add("dragging-active");
    setStatus("正在拖动，移动到目标位置后松开即可。");
    scheduleMove(event.clientY);
  }

  function finishDrag(message) {
    if (!dragged) return;
    const dropped = dragged;
    if (moveFrame) {
      window.cancelAnimationFrame(moveFrame);
      moveFrame = null;
    }
    if (activeDragElement && activePointerId !== null) {
      try {
        activeDragElement.releasePointerCapture(activePointerId);
      } catch (error) {
        // Pointer capture can already be released by the browser.
      }
    }
    dropped.classList.remove("dragging");
    dropped.classList.add("drop-bounce");
    window.setTimeout(() => dropped.classList.remove("drop-bounce"), 300);
    list.classList.remove("dragging-active");
    clearDragOver();
    stopAutoScroll();
    dragged = null;
    activeDragElement = null;
    activePointerId = null;
    pendingClientY = null;
    sync();
    setStatus(message || "排序已更新。");
  }

  list.addEventListener("pointerdown", beginDrag);

  document.addEventListener("pointermove", (event) => {
    if (!dragged || event.pointerId !== activePointerId) return;
    event.preventDefault();
    updateAutoScroll(event.clientY);
    scheduleMove(event.clientY);
  });

  document.addEventListener("pointerup", (event) => {
    if (!dragged || event.pointerId !== activePointerId) return;
    finishDrag("排序已更新。");
  });

  document.addEventListener("pointercancel", (event) => {
    if (!dragged || event.pointerId !== activePointerId) return;
    finishDrag("排序已更新。");
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-move]");
    if (!button) return;
    const item = button.closest("[data-topic-id]");
    if (button.dataset.move === "up" && item.previousElementSibling) {
      animateReorder(() => list.insertBefore(item, item.previousElementSibling));
    } else if (button.dataset.move === "down" && item.nextElementSibling) {
      animateReorder(() => list.insertBefore(item.nextElementSibling, item));
    }
    sync();
    flashMoved(item);
    const titleElement = item.querySelector(".topic-content h3");
    const title = titleElement ? titleElement.textContent : "话题";
    setStatus(`${title} 已移动到第 ${items().indexOf(item) + 1} 位。`);
  });

  sync();
})();
