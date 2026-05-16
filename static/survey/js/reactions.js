(function () {
  function syncGroup(group, value) {
    const input = group.querySelector('input[type="hidden"]');
    if (input) input.value = value;
    group.querySelectorAll("[data-reaction]").forEach((button) => {
      const selected = button.dataset.reaction === value;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", selected ? "true" : "false");
    });
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-reaction]");
    if (!button) return;
    const group = button.closest(".reaction-group");
    if (!group) return;
    const input = group.querySelector('input[type="hidden"]');
    const currentValue = input ? input.value : "none";
    const nextValue = currentValue === button.dataset.reaction ? "none" : button.dataset.reaction;
    syncGroup(group, nextValue);
  });

  document.querySelectorAll(".reaction-group").forEach((group) => {
    const input = group.querySelector('input[type="hidden"]');
    syncGroup(group, input && input.value ? input.value : "none");
  });
})();
