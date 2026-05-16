from django import forms
from django.contrib import admin
from django.db import models

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
    list_filter = ("is_enabled",)
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
    fields = ("name", "api_key", "usage_count", "is_active", "last_used_at")
    readonly_fields = ("usage_count", "last_used_at")


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    form = LLMProviderForm
    list_display = ("name", "model_name", "base_url", "key_count", "is_system_active", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "model_name", "base_url")
    fieldsets = (
        ("配置向导", {
            "fields": ("api_format", "model_preset"),
            "description": '第一步：选择API格式，第二步：选择模型'
        }),
        ("详细配置", {
            "fields": ("name", "model_name", "base_url", "is_active"),
            "description": '自动填充的配置信息，选择"自定义"时可手动修改'
        }),
        ("时间信息", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [APIKeyInline]

    def key_count(self, obj):
        return obj.api_keys.filter(is_active=True).count()
    key_count.short_description = "可用Key数量"

    def is_system_active(self, obj):
        """显示是否为当前系统使用的提供商"""
        config = SystemAPIConfig.get_instance()
        if config.active_provider_id == obj.pk:
            return "✓ 系统当前使用"
        return ""
    is_system_active.short_description = "系统状态"

    def changelist_view(self, request, extra_context=None):
        """在列表顶部显示当前系统配置"""
        extra_context = extra_context or {}
        config = SystemAPIConfig.get_instance()
        extra_context['system_config'] = config
        extra_context['system_api_change_url'] = f"/admin/experiments/systemapiconfig/{config.pk}/change/"
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        """根据API格式和模型预设自动填充字段"""
        api_format = form.cleaned_data.get('api_format')
        model_preset = form.cleaned_data.get('model_preset')

        # 如果是新建
        if not change:
            # 根据API格式设置base_url
            if api_format and api_format != 'custom':
                if api_format == 'openai':
                    obj.base_url = form.BASE_URL_PRESETS['openai']
                elif api_format == 'anthropic':
                    obj.base_url = form.BASE_URL_PRESETS['anthropic']

            # 根据模型预设设置model_name和name
            if model_preset and model_preset != 'custom':
                obj.model_name = model_preset
                # 智能生成名称
                if model_preset.startswith('gpt-5'):
                    obj.name = 'GPT-5'
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['openai']
                elif model_preset.startswith('gpt-4'):
                    obj.name = 'GPT-4'
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['openai']
                elif 'claude' in model_preset and '4-5' in model_preset:
                    obj.name = 'Claude 4.5'
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['anthropic']
                elif 'claude' in model_preset and ('4' in model_preset or '3' in model_preset):
                    obj.name = f"Claude {model_preset.split('-')[1]}"
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['anthropic']
                elif 'deepseek' in model_preset:
                    obj.name = 'DeepSeek'
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['deepseek']
                elif 'qwen' in model_preset:
                    obj.name = 'Qwen'
                    if not obj.base_url:
                        obj.base_url = form.BASE_URL_PRESETS['qwen']

        super().save_model(request, obj, form, change)


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
    list_filter = ("is_enabled",)
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

