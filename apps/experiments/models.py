import hashlib

from django.db import models


class ExperimentBatch(models.Model):
    TOPIC_STRATEGY_HIGHEST_LOWEST = "highest_lowest"
    ROUND_RANDOM = "random"
    NEUTRALITY_MODERATE = "moderate"
    NEUTRALITY_STRICT = "strict"

    name = models.CharField("批次名称", max_length=200)
    is_active = models.BooleanField("启用", default=True)
    intro_zh = models.TextField("第 1 步说明（中文）", blank=True)
    intro_en = models.TextField("第 1 步说明（英文）", blank=True)
    outro_zh = models.TextField("结束说明（中文）", blank=True)
    outro_en = models.TextField("结束说明（英文）", blank=True)
    english_paper_prompt = models.TextField(
        "英文论文要求",
        default="Write an English argumentative essay based on the discussion you completed.",
    )
    english_paper_duration_hours = models.PositiveIntegerField("英文论文时长（小时）", default=24)
    topic_selection_strategy = models.CharField("话题选择策略", max_length=40, default=TOPIC_STRATEGY_HIGHEST_LOWEST)
    round_order_strategy = models.CharField("轮次顺序策略", max_length=40, default=ROUND_RANDOM)
    ai_neutrality = models.CharField("AI 中立性", max_length=40, default=NEUTRALITY_MODERATE)
    ai_chat_minutes = models.PositiveIntegerField("AI 对话时长（分钟）", default=5)
    export_settings = models.JSONField("导出设置", default=dict, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "实验批次"
        verbose_name_plural = "实验批次"

    def __str__(self):
        return self.name


class Topic(models.Model):
    batches = models.ManyToManyField(
        ExperimentBatch,
        related_name="topics",
        verbose_name="所属批次",
        blank=True,
        help_text="一个话题可以同时属于多个批次。",
    )
    title_zh = models.CharField("话题标题（中文）", max_length=200)
    title_en = models.CharField("话题标题（英文）", max_length=200, blank=True)
    is_enabled = models.BooleanField("启用", default=True)
    position = models.PositiveIntegerField("排序", default=0)
    post_body_zh = models.TextField("帖子正文（中文）", blank=True)
    post_body_en = models.TextField("帖子正文（英文）", blank=True)
    statement_zh = models.TextField("观点陈述（中文）", blank=True)
    statement_en = models.TextField("观点陈述（英文）", blank=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "话题"
        verbose_name_plural = "话题"

    def __str__(self):
        return self.title_zh

    def snapshot(self):
        return {
            "id": self.pk,
            "title_zh": self.title_zh,
            "title_en": self.title_en,
            "post_body_zh": self.post_body_zh,
            "post_body_en": self.post_body_en,
            "statement_zh": self.statement_zh,
            "statement_en": self.statement_en,
            "comments": [comment.snapshot() for comment in self.comments.all()],
        }


class TopicComment(models.Model):
    TIMES = ["刚刚", "5 分钟前", "18 分钟前", "1 小时前", "昨天"]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="comments", verbose_name="话题")
    body_zh = models.TextField("评论（中文）")
    body_en = models.TextField("评论（英文）", blank=True)
    position = models.PositiveIntegerField("排序", default=0)
    auto_author_name = models.CharField("作者昵称", max_length=80, blank=True)
    avatar_seed = models.CharField("头像种子", max_length=120, blank=True)
    like_count = models.PositiveIntegerField("点赞数", default=0)
    relative_time = models.CharField("相对时间", max_length=40, blank=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "话题评论"
        verbose_name_plural = "话题评论"

    def save(self, *args, **kwargs):
        seed_source = f"{self.topic_id}:{self.position}:{self.body_zh[:20]}"
        digest = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()
        number = int(digest[:8], 16)
        if not self.avatar_seed:
            self.avatar_seed = digest[:12]
        if not self.like_count:
            self.like_count = number % 300
        if not self.relative_time:
            self.relative_time = self.TIMES[number % len(self.TIMES)]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.body_zh[:30]

    def snapshot(self):
        return {
            "id": self.pk,
            "body_zh": self.body_zh,
            "body_en": self.body_en,
            "author": "",
            "avatar_seed": self.avatar_seed,
            "like_count": self.like_count,
            "relative_time": self.relative_time,
        }


class ScaleItem(models.Model):
    EMOTION = "emotion"
    STANCE = "stance"
    AI_EVAL = "ai_eval"
    TYPES = [(EMOTION, "情绪量表"), (STANCE, "观点量表"), (AI_EVAL, "AI 评价量表")]

    batch = models.ForeignKey(ExperimentBatch, on_delete=models.CASCADE, related_name="scale_items", verbose_name="批次")
    item_type = models.CharField("量表类型", max_length=30, choices=TYPES)
    label_zh = models.CharField("题目（中文）", max_length=200)
    label_en = models.CharField("题目（英文）", max_length=200, blank=True)
    min_value = models.IntegerField("最小值", default=1)
    max_value = models.IntegerField("最大值", default=7)
    left_label_zh = models.CharField("左侧标签（中文）", max_length=100, blank=True)
    right_label_zh = models.CharField("右侧标签（中文）", max_length=100, blank=True)
    position = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ["item_type", "position", "id"]
        verbose_name = "量表题目"
        verbose_name_plural = "量表题目"

    def __str__(self):
        return self.label_zh


class RatingScaleConfig(models.Model):
    batch = models.OneToOneField(ExperimentBatch, on_delete=models.CASCADE, related_name="rating_config", verbose_name="批次")
    stance_min = models.IntegerField("同意度最小值", default=1)
    stance_max = models.IntegerField("同意度最大值", default=7)
    certainty_min = models.IntegerField("确定度最小值", default=1)
    certainty_max = models.IntegerField("确定度最大值", default=7)

    class Meta:
        verbose_name = "评分配置"
        verbose_name_plural = "评分配置"


class AIMode(models.Model):
    batch = models.ForeignKey(ExperimentBatch, on_delete=models.CASCADE, related_name="ai_modes", verbose_name="批次")
    name_zh = models.CharField("模式名称（中文）", max_length=120)
    name_en = models.CharField("模式名称（英文）", max_length=120, blank=True)
    prompt_zh = models.TextField("提示词（中文）")
    prompt_en = models.TextField("提示词（英文）", blank=True)
    position = models.PositiveIntegerField("排序", default=0)
    is_enabled = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "AI 模式 (Prompt配置)"
        verbose_name_plural = "AI 模式 (Prompt配置)"

    def __str__(self):
        return self.name_zh


class SystemAPIConfig(models.Model):
    """系统级API配置 - 单例模型"""
    active_provider = models.ForeignKey(
        'LLMProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_configs',
        verbose_name='当前使用的LLM提供商',
        help_text='选择系统统一使用的AI模型提供商'
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "系统API配置"
        verbose_name_plural = "系统API配置"

    def __str__(self):
        if self.active_provider:
            return f"当前使用: {self.active_provider.name}"
        return "未配置API"

    def save(self, *args, **kwargs):
        # 确保只有一条记录（单例模式）
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class LLMProvider(models.Model):
    """LLM模型提供商配置"""
    name = models.CharField("提供商名称", max_length=120, unique=True, help_text="例如: GPT-4, Claude, Qwen等")
    model_name = models.CharField("模型名称", max_length=200, help_text="调用API时使用的模型标识，例如: gpt-4, claude-3-opus")
    base_url = models.URLField("API Base URL", help_text="模型API的基础URL")
    priority = models.PositiveIntegerField("调用顺序", default=0, help_text="数字越小越优先调用")
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "LLM 提供商"
        verbose_name_plural = "LLM 提供商"
        ordering = ["priority", "id"]

    def __str__(self):
        return f"{self.name} ({self.model_name})"

    def get_next_api_key(self, model_name=None):
        """获取下一个可用的API Key（轮询分配）"""
        from django.db import transaction
        from django.db.models import F

        with transaction.atomic():
            # 获取所有启用的key，按使用次数排序
            keys = list(self.api_keys.filter(is_active=True).select_for_update().order_by('usage_count', 'id'))
            if model_name:
                keys = [key for key in keys if key.supports_model(model_name)]

            if not keys:
                if model_name:
                    raise ValueError(f"提供商 {self.name} 没有启用且支持 {model_name} 的 API Key")
                raise ValueError(f"提供商 {self.name} 没有可用的API Key")

            # 获取使用次数最少的key
            selected_key = keys[0]

            # 增加使用计数
            selected_key.usage_count = F('usage_count') + 1
            selected_key.save(update_fields=['usage_count'])

            # 刷新以获取实际的usage_count值
            selected_key.refresh_from_db()

            return selected_key


class APIKey(models.Model):
    """API Key池，支持多个key的负载均衡"""
    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        related_name='api_keys',
        verbose_name='LLM 提供商'
    )
    api_key = models.CharField("API Key", max_length=500)
    model_name = models.TextField("支持模型", blank=True)
    name = models.CharField("Key名称", max_length=120, blank=True, help_text="便于识别的key名称，例如: key-1, key-2")
    usage_count = models.PositiveIntegerField("使用次数", default=0, help_text="记录该key被使用的次数，用于轮询分配")
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    last_used_at = models.DateTimeField("最后使用时间", null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ['provider', 'usage_count', 'id']

    def __str__(self):
        key_preview = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else self.api_key
        name_part = f" ({self.name})" if self.name else ""
        return f"{self.provider.name} - {key_preview}{name_part}"

    def model_names(self):
        normalized = (self.model_name or "").replace("，", ",").replace("；", ";").replace("\r\n", "\n")
        parts = []
        for line in normalized.replace(";", "\n").replace(",", "\n").split("\n"):
            value = line.strip()
            if value:
                parts.append(value)
        return parts

    def default_model_name(self):
        models = self.model_names()
        if models:
            return models[0]
        return self.provider.model_name

    def supports_model(self, model_name):
        if not model_name:
            return True
        return model_name == self.default_model_name() or model_name in self.model_names()

