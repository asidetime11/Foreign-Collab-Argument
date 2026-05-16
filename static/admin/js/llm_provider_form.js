(function() {
    'use strict';

    // OAI格式的模型列表
    const OAI_MODELS = [
        {value: '', label: '--- 选择模型 ---'},
        {value: 'gpt-5-turbo', label: 'GPT-5 Turbo', name: 'GPT-5'},
        {value: 'gpt-5', label: 'GPT-5', name: 'GPT-5'},
        {value: 'gpt-4o', label: 'GPT-4o', name: 'GPT-4'},
        {value: 'gpt-4-turbo', label: 'GPT-4 Turbo', name: 'GPT-4'},
        {value: 'gpt-4', label: 'GPT-4', name: 'GPT-4'},
        {value: 'deepseek-chat', label: 'DeepSeek Chat', name: 'DeepSeek'},
        {value: 'deepseek-reasoner', label: 'DeepSeek Reasoner', name: 'DeepSeek'},
        {value: 'qwen-max', label: 'Qwen Max', name: 'Qwen'},
        {value: 'qwen-plus', label: 'Qwen Plus', name: 'Qwen'},
        {value: 'qwen-turbo', label: 'Qwen Turbo', name: 'Qwen'},
        {value: 'custom', label: '🔧 自定义'},
    ];

    // Anthropic格式的模型列表
    const ANTHROPIC_MODELS = [
        {value: '', label: '--- 选择模型 ---'},
        {value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5', name: 'Claude 4.5'},
        {value: 'claude-opus-4-20250514', label: 'Claude Opus 4', name: 'Claude 4'},
        {value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', name: 'Claude 3.5'},
        {value: 'claude-3-opus-20240229', label: 'Claude 3 Opus', name: 'Claude 3'},
        {value: 'custom', label: '🔧 自定义'},
    ];

    // API地址预设
    const BASE_URLS = {
        'openai': 'https://api.openai.com/v1',
        'anthropic': 'https://api.anthropic.com/v1',
        'deepseek': 'https://api.deepseek.com/v1',
        'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    };

    function initForm() {
        const apiFormatSelect = document.getElementById('id_api_format');
        const modelPresetSelect = document.getElementById('id_model_preset');
        const nameField = document.getElementById('id_name');
        const modelNameField = document.getElementById('id_model_name');
        const baseUrlField = document.getElementById('id_base_url');

        if (!apiFormatSelect || !modelPresetSelect) return;

        // 更新模型列表
        function updateModelList(format) {
            const models = format === 'anthropic' ? ANTHROPIC_MODELS : OAI_MODELS;
            const currentValue = modelPresetSelect.value;

            // 清空现有选项
            modelPresetSelect.innerHTML = '';

            // 添加新选项
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.value;
                option.textContent = model.label;
                modelPresetSelect.appendChild(option);
            });

            // 尝试保持之前的选择
            if (currentValue && modelPresetSelect.querySelector(`option[value="${currentValue}"]`)) {
                modelPresetSelect.value = currentValue;
            }
        }

        // API格式改变时
        apiFormatSelect.addEventListener('change', function() {
            const format = this.value;

            if (format === 'custom') {
                // 选择自定义，清空让用户填写
                baseUrlField.focus();
            } else if (format && format !== '') {
                // 选择预设格式
                updateModelList(format);

                // 设置对应的base_url
                if (format === 'openai') {
                    baseUrlField.value = BASE_URLS.openai;
                } else if (format === 'anthropic') {
                    baseUrlField.value = BASE_URLS.anthropic;
                }

                // 重置模型选择
                modelPresetSelect.value = '';
            }
        });

        // 模型改变时
        modelPresetSelect.addEventListener('change', function() {
            const value = this.value;

            if (value === 'custom') {
                // 选择自定义，清空让用户填写
                if (!modelNameField.value) {
                    modelNameField.value = '';
                }
                if (!nameField.value) {
                    nameField.value = '';
                }
                modelNameField.focus();
            } else if (value && value !== '') {
                // 选择预设模型
                const apiFormat = apiFormatSelect.value;
                const models = apiFormat === 'anthropic' ? ANTHROPIC_MODELS : OAI_MODELS;
                const selectedModel = models.find(m => m.value === value);

                if (selectedModel) {
                    // 填充model_name
                    modelNameField.value = value;

                    // 填充name
                    if (selectedModel.name) {
                        nameField.value = selectedModel.name;
                    }

                    // 根据模型设置合适的base_url
                    if (value.startsWith('deepseek')) {
                        baseUrlField.value = BASE_URLS.deepseek;
                    } else if (value.startsWith('qwen')) {
                        baseUrlField.value = BASE_URLS.qwen;
                    } else if (value.startsWith('gpt')) {
                        baseUrlField.value = BASE_URLS.openai;
                    } else if (value.includes('claude')) {
                        baseUrlField.value = BASE_URLS.anthropic;
                    }
                }
            }
        });

        // 为字段添加样式提示
        function updateFieldStyle(field, isEmpty) {
            if (isEmpty) {
                field.style.borderColor = '#ffa500';
                field.style.backgroundColor = '#fffef0';
            } else {
                field.style.borderColor = '';
                field.style.backgroundColor = '';
            }
        }

        // 监听name字段变化
        nameField.addEventListener('input', function() {
            const isEmpty = !this.value.trim();
            updateFieldStyle(this, isEmpty && modelPresetSelect.value === 'custom');
        });

        // 监听model_name字段变化
        modelNameField.addEventListener('input', function() {
            const isEmpty = !this.value.trim();
            updateFieldStyle(this, isEmpty && modelPresetSelect.value === 'custom');
        });

        // 监听base_url字段变化
        baseUrlField.addEventListener('input', function() {
            const isEmpty = !this.value.trim();
            updateFieldStyle(this, isEmpty && apiFormatSelect.value === 'custom');
        });
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initForm);
    } else {
        initForm();
    }
})();
