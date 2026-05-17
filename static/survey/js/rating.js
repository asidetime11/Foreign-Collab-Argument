// rating.js - Simplified slider without floating bubbles
(function() {
  'use strict';

  document.addEventListener('DOMContentLoaded', initSliders);

  function initSliders() {
    const sliders = document.querySelectorAll('.scale-slider');

    sliders.forEach(slider => {
      // Initialize display
      updateSliderDisplay(slider);

      // Listen to input events
      slider.addEventListener('input', () => updateSliderDisplay(slider));

      // Show progress bar when dragging
      slider.addEventListener('mousedown', () => {
        slider.classList.add('dragging');
      });

      slider.addEventListener('touchstart', () => {
        slider.classList.add('dragging');
      });

      // Hide progress bar when released and update display
      const stopDragging = () => {
        slider.classList.remove('dragging');
        // Force update display to ensure answered state is applied
        setTimeout(() => {
          updateSliderDisplay(slider);
        }, 10);
      };

      slider.addEventListener('mouseup', stopDragging);
      slider.addEventListener('touchend', stopDragging);

      // Also stop dragging if mouse leaves the document
      document.addEventListener('mouseup', stopDragging);
    });

    // Form validation
    const forms = document.querySelectorAll('.rating-form');
    forms.forEach(form => {
      const alert = form.querySelector('.soft-alert');

      form.addEventListener("submit", (event) => {
        const missingInputs = Array.from(form.querySelectorAll('.rating-value')).filter(input => !input.value);
        if (!missingInputs.length) return;

        event.preventDefault();
        if (alert) {
          alert.hidden = false;
          alert.textContent = '请先完成所有滑杆，再继续。';
        }

        const firstMissing = missingInputs[0].closest('.scale-question');
        if (firstMissing) {
          const slider = firstMissing.querySelector('.scale-slider');
          if (slider) slider.focus();
        }
      });
    });
  }

  function updateSliderDisplay(slider) {
    if (!slider) return;

    const value = parseInt(slider.value);
    const min = parseInt(slider.min);
    const max = parseInt(slider.max);

    // Update ARIA attribute
    slider.setAttribute('aria-valuenow', value);

    // Update track fill using CSS custom property on the slider itself
    const percent = ((value - min) / (max - min)) * 100;
    slider.style.setProperty('--slider-percent', percent + '%');

    // Highlight current number
    const container = slider.closest('.scale-question');
    if (!container) return;

    const readout = container.querySelector('[data-scale-value]');
    if (readout) {
      readout.textContent = value;
    }

    const numbers = container.querySelectorAll('.number-label');
    numbers.forEach(label => {
      const labelValue = parseInt(label.dataset?.value || '0');
      if (labelValue === value) {
        label.classList.add('active');
      } else {
        label.classList.remove('active');
      }
    });

    // Update hidden input for form submission
    const hiddenInput = container.querySelector('.rating-value');
    if (hiddenInput) {
      hiddenInput.value = value;
    }

    // Mark as answered
    container.classList.add('answered');
  }
})();
