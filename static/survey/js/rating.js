(function () {
  document.querySelectorAll(".rating-card").forEach((field) => {
    const input = field.querySelector('input[type="hidden"]');
    const slider = field.querySelector('input[type="range"]');
    const readout = field.querySelector(".rating-value");
    if (!input || !slider || !readout) return;
    const sliderWrap = slider.closest(".rating-slider");

    function updateProgress() {
      const min = Number(slider.min || 1);
      const max = Number(slider.max || 7);
      const value = Number(slider.value || min);
      const percent = max === min ? 0 : ((value - min) / (max - min)) * 100;
      if (sliderWrap) sliderWrap.style.setProperty("--rating-percent", `${percent}%`);
    }

    function sync() {
      input.value = slider.value;
      readout.textContent = slider.value;
      field.classList.add("answered");
      slider.classList.add("answered");
      if (sliderWrap) sliderWrap.classList.add("answered");
      updateProgress();
    }

    updateProgress();
    slider.addEventListener("input", sync);
    slider.addEventListener("change", sync);
  });

  document.querySelectorAll(".rating-form").forEach((form) => {
    const alert = form.querySelector(".soft-alert");

    form.addEventListener("submit", (event) => {
      const missing = Array.from(form.querySelectorAll('.rating-card input[type="hidden"]')).filter((input) => !input.value);
      if (!missing.length) return;

      event.preventDefault();
      if (alert) {
        alert.hidden = false;
        alert.textContent = "请先完成所有滑杆，再继续。";
      }
      const firstMissing = missing[0].closest(".rating-card");
      if (firstMissing) {
        firstMissing.classList.add("needs-answer");
        const slider = firstMissing.querySelector('input[type="range"]');
        if (slider) slider.focus();
      }
    });
  });
})();
