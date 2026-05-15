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
    batch = models.ForeignKey(ExperimentBatch, on_delete=models.CASCADE, related_name="topics", verbose_name="批次")
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
    AUTHORS = ["林一", "陈晨", "周明", "小雨", "Alex", "Mina"]
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
        if not self.auto_author_name:
            self.auto_author_name = self.AUTHORS[number % len(self.AUTHORS)]
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
            "author": self.auto_author_name,
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
        verbose_name = "AI 模式"
        verbose_name_plural = "AI 模式"

    def __str__(self):
        return self.name_zh
