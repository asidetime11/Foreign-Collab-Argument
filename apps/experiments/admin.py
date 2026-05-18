from django import forms
from django.contrib import admin, messages
from django.db import models
from django.shortcuts import redirect
from django.urls import path, reverse

from .admin_views import default_batch
from .models import AIMode, APIKey, LLMProvider, SystemAPIConfig, Topic, TopicComment


class LLMProviderForm(forms.ModelForm):
    """LLM提供商表单，提供常见选项"""

    API_FORMAT_CHOICES = [
        ('', '--- 选择API格式 ---'),
        ('openai', 'OpenAI 格式 (OAI)'),
        ('anthropic', 'Anthropic 格式'),
        ('custom', '🔧 自定义'),
    ]

    # OpenAI格式的模型
    OAI_MODEL_CHOICES = [
        ('', '--- 选择模型 ---'),
        ('gpt-5-turbo', 'GPT-5 Turbo'),
        ('gpt-5', 'GPT-5'),
        ('gpt-4o', 'GPT-4o'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('deepseek-chat', 'DeepSeek Chat'),
        ('deepseek-reasoner', 'DeepSeek Reasoner'),
        ('qwen-max', 'Qwen Max'),
        ('qwen-plus', 'Qwen Plus'),
        ('qwen-turbo', 'Qwen Turbo'),
        ('custom', '🔧 自定义'),
    ]

    # Anthropic格式的模型
    ANTHROPIC_MODEL_CHOICES = [
        ('', '--- 选择模型 ---'),
        ('claude-sonnet-4-5-20250929', 'Claude Sonnet 4.5'),
        ('claude-opus-4-20250514', 'Claude Opus 4'),
        ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet'),
        ('claude-3-opus-20240229', 'Claude 3 Opus'),
        ('custom', '🔧 自定义'),
    ]

    BASE_URL_PRESETS = {
        'openai': 'https://api.openai.com/v1',
        'anthropic': 'https://api.anthropic.com/v1',
        'deepseek': 'https://api.deepseek.com/v1',
        'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    }

    api_format = forms.ChoiceField(
        choices=API_FORMAT_CHOICES,
        required=False,
        label='API格式',
        help_text='选择API调用格式'
    )

    model_preset = forms.ChoiceField(
        choices=[],  # 动态设置
        required=False,
        label='模型',
        help_text='选择模型，或选择"自定义"后在下方填写'
    )

    class Meta:
        model = LLMProvider
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '例如: GPT-5', 'size': '40'}),
            'model_name': forms.TextInput(attrs={'placeholder': '例如: gpt-5-turbo', 'size': '40'}),
            'base_url': forms.URLInput(attrs={'placeholder': 'https://api.openai.com/v1', 'size': '60'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 默认使用OAI格式的模型列表
        self.fields['model_preset'].choices = self.OAI_MODEL_CHOICES

        # 如果是编辑已存在的提供商
        if self.instance.pk:
            # 根据base_url推断API格式
            if 'anthropic' in self.instance.base_url:
                self.initial['api_format'] = 'anthropic'
                self.fields['model_preset'].choices = self.ANTHROPIC_MODEL_CHOICES
            elif 'openai' in self.instance.base_url or 'deepseek' in self.instance.base_url or 'dashscope' in self.instance.base_url:
                self.initial['api_format'] = 'openai'
                self.fields['model_preset'].choices = self.OAI_MODEL_CHOICES
            else:
                self.initial['api_format'] = 'custom'

            # 检查模型是否匹配预设
            all_models = dict(self.OAI_MODEL_CHOICES + self.ANTHROPIC_MODEL_CHOICES)
            if self.instance.model_name in all_models:
                self.initial['model_preset'] = self.instance.model_name
            else:
                self.initial['model_preset'] = 'custom'

    class Media:
        js = ('admin/js/llm_provider_form.js',)



class TopicCommentInline(admin.TabularInline):
    model = TopicComment
    extra = 0
    exclude = ("avatar_seed", "auto_author_name")
    fields = ("body_zh", "body_en", "position", "like_count", "relative_time")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3})},
    }


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title_zh", "is_enabled", "position")
    actions = None
    search_fields = ("title_zh", "title_en")
    fieldsets = (
        ("话题", {"fields": ("title_zh", "title_en", "is_enabled", "position")}),
        ("帖子与观点", {"fields": ("statement_zh", "statement_en", "post_body_zh", "post_body_en")}),
    )
    inlines = [TopicCommentInline]

    def save_model(self, request, obj, form, change):
        if not obj.batch_id:
            obj.batch = default_batch()
        super().save_model(request, obj, form, change)


class APIKeyInline(admin.TabularInline):
    model = APIKey
    extra = 1
    fields = ("api_key", "model_name")
    min_num = 1
    validate_min = True
    formfield_overrides = {
        models.TextField: {
            "widget": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "每行一个模型，例如：\ngpt-5\nwhisper-1\nqwen-plus",
                }
            )
        },
    }


class SimpleLLMProviderForm(forms.ModelForm):
    class Meta:
        model = LLMProvider
        fields = ("base_url",)
        labels = {
            "base_url": "URL",
        }
        help_texts = {
            "base_url": "",
        }
        widgets = {
            "base_url": forms.URLInput(attrs={"placeholder": "https://api.example.com/v1"}),
        }


class CostEffectiveLLMProviderForm(forms.ModelForm):
    API_FORMAT_CHOICES = [
        ("", "--- 选择服务商/API格式 ---"),
        ("openai", "OpenAI"),
        ("deepseek", "DeepSeek（OpenAI 兼容）"),
        ("qwen", "Qwen/通义千问（OpenAI 兼容）"),
        ("anthropic", "Anthropic"),
        ("custom", "自定义"),
    ]
    OAI_MODEL_CHOICES = [
        ("", "--- 选择模型 ---"),
        ("gpt-5.4-mini", "GPT-5.4 mini（推荐：质量/成本均衡）"),
        ("gpt-5-mini", "GPT-5 mini（性价比通用）"),
        ("gpt-5-nano", "GPT-5 nano（低成本快速）"),
        ("custom", "自定义"),
    ]
    DEEPSEEK_MODEL_CHOICES = [
        ("", "--- 选择模型 ---"),
        ("deepseek-chat", "DeepSeek Chat（低成本通用）"),
        ("deepseek-reasoner", "DeepSeek Reasoner（推理任务）"),
        ("custom", "自定义"),
    ]
    QWEN_MODEL_CHOICES = [
        ("", "--- 选择模型 ---"),
        ("qwen-plus", "Qwen Plus（中文/通用性价比）"),
        ("qwen-turbo", "Qwen Turbo（低成本快速）"),
        ("qwen-max", "Qwen Max（质量优先）"),
        ("custom", "自定义"),
    ]
    ANTHROPIC_MODEL_CHOICES = [
        ("", "--- 选择模型 ---"),
        ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5（质量优先）"),
        ("custom", "自定义"),
    ]
    BASE_URL_PRESETS = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "anthropic": "https://api.anthropic.com/v1",
    }
    MODEL_CHOICES_BY_FORMAT = {
        "openai": OAI_MODEL_CHOICES,
        "deepseek": DEEPSEEK_MODEL_CHOICES,
        "qwen": QWEN_MODEL_CHOICES,
        "anthropic": ANTHROPIC_MODEL_CHOICES,
    }
    MODEL_DISPLAY_NAMES = {
        "gpt-5.4-mini": "OpenAI GPT-5.4 mini",
        "gpt-5-mini": "OpenAI GPT-5 mini",
        "gpt-5-nano": "OpenAI GPT-5 nano",
        "deepseek-chat": "DeepSeek Chat",
        "deepseek-reasoner": "DeepSeek Reasoner",
        "qwen-plus": "Qwen Plus",
        "qwen-turbo": "Qwen Turbo",
        "qwen-max": "Qwen Max",
        "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    }

    api_format = forms.ChoiceField(
        choices=API_FORMAT_CHOICES,
        required=False,
        label="服务商/API格式",
        help_text="先选择服务商，系统会自动填入常用 Base URL。",
    )
    model_preset = forms.ChoiceField(
        choices=OAI_MODEL_CHOICES,
        required=False,
        label="推荐模型",
        help_text="可直接选择推荐模型，也可以选择“自定义”后手动填写模型名。",
    )

    class Meta:
        model = LLMProvider
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "例如：OpenAI GPT-5 mini", "size": "40"}),
            "model_name": forms.TextInput(attrs={"placeholder": "例如：gpt-5-mini", "size": "40"}),
            "base_url": forms.URLInput(attrs={"placeholder": "https://api.openai.com/v1", "size": "60"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_format = self._initial_api_format()
        self.initial["api_format"] = api_format
        self.fields["model_preset"].choices = self.MODEL_CHOICES_BY_FORMAT.get(api_format, self.OAI_MODEL_CHOICES)
        if self.instance.pk:
            all_models = dict(
                self.OAI_MODEL_CHOICES
                + self.DEEPSEEK_MODEL_CHOICES
                + self.QWEN_MODEL_CHOICES
                + self.ANTHROPIC_MODEL_CHOICES
            )
            self.initial["model_preset"] = self.instance.model_name if self.instance.model_name in all_models else "custom"

    def _initial_api_format(self):
        if not self.instance.pk:
            return "openai"
        base_url = self.instance.base_url or ""
        if "deepseek" in base_url:
            return "deepseek"
        if "dashscope" in base_url or "qwen" in base_url:
            return "qwen"
        if "anthropic" in base_url:
            return "anthropic"
        if "openai" in base_url:
            return "openai"
        return "custom"

    class Media:
        js = ("admin/js/llm_provider_form.js",)


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    form = SimpleLLMProviderForm
    change_list_template = "admin/experiments/llmprovider/change_list.html"
    change_form_template = "admin/experiments/llmprovider/change_form.html"
    list_display = ("priority", "name", "base_url", "key_count", "is_active", "created_at")
    actions = None
    search_fields = ("name", "model_name", "base_url")
    fields = ("base_url",)
    inlines = [APIKeyInline]

    def key_count(self, obj):
        return obj.api_keys.filter(is_active=True).count()
    key_count.short_description = "可用Key数量"

    @staticmethod
    def key_preview(value):
        if len(value) > 12:
            return f"{value[:8]}...{value[-4:]}"
        return value

    def provider_rows(self, queryset):
        rows = []
        for index, provider in enumerate(queryset.prefetch_related("api_keys"), start=1):
            keys = list(provider.api_keys.all())
            active_keys = [key for key in keys if key.is_active]
            last_used_values = [key.last_used_at for key in keys if key.last_used_at]
            previews = [self.key_preview(key.api_key) for key in active_keys[:3]]
            models = sorted(
                {
                    model
                    for key in active_keys
                    for model in (key.model_names() or ([provider.model_name] if provider.model_name else []))
                }
            )
            rows.append(
                {
                    "order": index,
                    "provider": provider,
                    "active_key_count": len(active_keys),
                    "key_preview": " / ".join(previews) if previews else "未配置启用 Key",
                    "model_preview": " / ".join(models) if models else "未配置模型",
                    "last_used_at": max(last_used_values) if last_used_values else None,
                }
            )
        return rows

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:provider_id>/move/<str:direction>/",
                self.admin_site.admin_view(self.move_provider),
                name="experiments_llmprovider_move",
            ),
            path(
                "<int:provider_id>/toggle/",
                self.admin_site.admin_view(self.toggle_provider),
                name="experiments_llmprovider_toggle",
            ),
        ]
        return custom_urls + urls

    def _renumber_priorities(self):
        for index, provider in enumerate(LLMProvider.objects.order_by("priority", "id"), start=1):
            if provider.priority != index:
                provider.priority = index
                provider.save(update_fields=["priority"])

    def move_provider(self, request, provider_id, direction):
        if request.method != "POST":
            return redirect("admin:experiments_llmprovider_changelist")
        self._renumber_priorities()
        providers = list(LLMProvider.objects.order_by("priority", "id"))
        index = next((idx for idx, provider in enumerate(providers) if provider.pk == provider_id), None)
        if index is None:
            messages.error(request, "没有找到这个 LLM 供应商。")
            return redirect("admin:experiments_llmprovider_changelist")
        target_index = index - 1 if direction == "up" else index + 1
        if 0 <= target_index < len(providers):
            current = providers[index]
            target = providers[target_index]
            current.priority, target.priority = target.priority, current.priority
            current.save(update_fields=["priority"])
            target.save(update_fields=["priority"])
            messages.success(request, "调用顺序已更新。")
        return redirect("admin:experiments_llmprovider_changelist")

    def toggle_provider(self, request, provider_id):
        if request.method != "POST":
            return redirect("admin:experiments_llmprovider_changelist")
        provider = LLMProvider.objects.get(pk=provider_id)
        provider.is_active = not provider.is_active
        provider.save(update_fields=["is_active"])
        messages.success(request, f"{provider.name} 已{'启用' if provider.is_active else '停用'}。")
        return redirect("admin:experiments_llmprovider_changelist")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request).order_by("priority", "id")
        extra_context["provider_rows"] = self.provider_rows(queryset)
        extra_context["add_url"] = reverse("admin:experiments_llmprovider_add")
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.name = self._unique_provider_name(obj.base_url, obj.pk)
        obj.is_active = True
        if not obj.priority:
            obj.priority = (LLMProvider.objects.exclude(pk=obj.pk).count() or 0) + 1
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        provider = form.instance
        first_key = provider.api_keys.filter(is_active=True).order_by("usage_count", "id").first()
        if first_key and first_key.default_model_name() and provider.model_name != first_key.default_model_name():
            provider.model_name = first_key.default_model_name()
            provider.save(update_fields=["model_name"])

    @staticmethod
    def _unique_provider_name(base_url, pk=None):
        base_name = (base_url or "").replace("https://", "").replace("http://", "").strip("/").split("/")[0] or "LLM"
        candidate = base_name
        suffix = 2
        existing = LLMProvider.objects.all()
        if pk:
            existing = existing.exclude(pk=pk)
        while existing.filter(name=candidate).exists():
            candidate = f"{base_name} {suffix}"
            suffix += 1
        return candidate


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("provider", "name", "key_preview", "usage_count", "is_active", "last_used_at")
    list_filter = ("is_active", "provider", "created_at")
    search_fields = ("name", "provider__name")
    fields = ("provider", "name", "api_key", "usage_count", "is_active", "created_at", "last_used_at")
    readonly_fields = ("usage_count", "created_at", "last_used_at")

    def key_preview(self, obj):
        if len(obj.api_key) > 12:
            return f"{obj.api_key[:8]}...{obj.api_key[-4:]}"
        return obj.api_key
    key_preview.short_description = "Key预览"


@admin.register(SystemAPIConfig)
class SystemAPIConfigAdmin(admin.ModelAdmin):
    """系统API配置管理 - 单例模式"""
    list_display = ("__str__", "active_provider", "updated_at")
    fieldsets = (
        ("系统API配置", {
            "fields": ("active_provider",),
            "description": "选择系统统一使用的AI模型提供商和配置。所有AI对话将使用此配置。"
        }),
        ("时间信息", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        # 单例模式：如果已经存在记录则不允许添加
        return not SystemAPIConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # 不允许删除系统配置
        return False


@admin.register(AIMode)
class AIModeAdmin(admin.ModelAdmin):
    list_display = ("name_zh", "is_enabled", "position")
    actions = None
    search_fields = ("name_zh", "prompt_zh")
    fieldsets = (
        ("基本信息", {
            "fields": ("name_zh", "name_en", "is_enabled", "position"),
            "description": "AI模式的基本配置"
        }),
        ("Prompt 配置", {
            "fields": ("prompt_zh", "prompt_en"),
            "description": "定义AI的行为和回复风格"
        }),
    )
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 8, "cols": 80})},
    }

    def save_model(self, request, obj, form, change):
        if not obj.batch_id:
            obj.batch = default_batch()
        super().save_model(request, obj, form, change)

