(function () {
  document.querySelectorAll(".rating").forEach(function (field) {
    const input = field.querySelector("input[type=hidden]");
    field.querySelectorAll("[data-value]").forEach(function (button) {
      button.addEventListener("click", function () {
        input.value = button.dataset.value;
        field.querySelectorAll("[data-value]").forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
      });
    });
  });
})();
