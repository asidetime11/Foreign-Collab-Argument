(function () {
  "use strict";

  const MODEL_GROUPS = {
    openai: [
      { value: "", label: "--- 选择模型 ---" },
      { value: "gpt-5.4-mini", label: "GPT-5.4 mini（推荐：质量/成本均衡）", name: "OpenAI GPT-5.4 mini" },
      { value: "gpt-5-mini", label: "GPT-5 mini（性价比通用）", name: "OpenAI GPT-5 mini" },
      { value: "gpt-5-nano", label: "GPT-5 nano（低成本快速）", name: "OpenAI GPT-5 nano" },
      { value: "custom", label: "自定义" },
    ],
    deepseek: [
      { value: "", label: "--- 选择模型 ---" },
      { value: "deepseek-chat", label: "DeepSeek Chat（低成本通用）", name: "DeepSeek Chat" },
      { value: "deepseek-reasoner", label: "DeepSeek Reasoner（推理任务）", name: "DeepSeek Reasoner" },
      { value: "custom", label: "自定义" },
    ],
    qwen: [
      { value: "", label: "--- 选择模型 ---" },
      { value: "qwen-plus", label: "Qwen Plus（中文/通用性价比）", name: "Qwen Plus" },
      { value: "qwen-turbo", label: "Qwen Turbo（低成本快速）", name: "Qwen Turbo" },
      { value: "qwen-max", label: "Qwen Max（质量优先）", name: "Qwen Max" },
      { value: "custom", label: "自定义" },
    ],
    anthropic: [
      { value: "", label: "--- 选择模型 ---" },
      { value: "claude-sonnet-4-5-20250929", label: "Claude Sonnet 4.5（质量优先）", name: "Claude Sonnet 4.5" },
      { value: "custom", label: "自定义" },
    ],
  };

  const BASE_URLS = {
    openai: "https://api.openai.com/v1",
    deepseek: "https://api.deepseek.com/v1",
    qwen: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    anthropic: "https://api.anthropic.com/v1",
  };

  function initForm() {
    const apiFormatSelect = document.getElementById("id_api_format");
    const modelPresetSelect = document.getElementById("id_model_preset");
    const nameField = document.getElementById("id_name");
    const modelNameField = document.getElementById("id_model_name");
    const baseUrlField = document.getElementById("id_base_url");

    if (!apiFormatSelect || !modelPresetSelect || !nameField || !modelNameField || !baseUrlField) return;

    function modelsFor(format) {
      return MODEL_GROUPS[format] || MODEL_GROUPS.openai;
    }

    function updateModelList(format) {
      const currentValue = modelPresetSelect.value;
      modelPresetSelect.innerHTML = "";
      modelsFor(format).forEach((model) => {
        const option = document.createElement("option");
        option.value = model.value;
        option.textContent = model.label;
        modelPresetSelect.appendChild(option);
      });
      if (currentValue && modelPresetSelect.querySelector(`option[value="${currentValue}"]`)) {
        modelPresetSelect.value = currentValue;
      } else {
        modelPresetSelect.value = "";
      }
    }

    function selectedModel() {
      return modelsFor(apiFormatSelect.value).find((model) => model.value === modelPresetSelect.value);
    }

    apiFormatSelect.addEventListener("change", function () {
      const format = this.value;
      updateModelList(format);
      if (BASE_URLS[format]) {
        baseUrlField.value = BASE_URLS[format];
      }
      if (format === "custom") {
        baseUrlField.focus();
      }
    });

    modelPresetSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        modelNameField.focus();
        return;
      }
      const model = selectedModel();
      if (!model || !model.value) return;
      modelNameField.value = model.value;
      nameField.value = model.name || model.value;
      if (BASE_URLS[apiFormatSelect.value]) {
        baseUrlField.value = BASE_URLS[apiFormatSelect.value];
      }
    });

    updateModelList(apiFormatSelect.value || "openai");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initForm);
  } else {
    initForm();
  }
})();
