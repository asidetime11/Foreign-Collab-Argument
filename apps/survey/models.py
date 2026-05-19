from django.conf import settings
from django.db import models


class SurveySession(models.Model):
    STEP_TOPIC_ORDER = "topic_order"
    STEP_ROUND = "round"
    STEP_ENGLISH_PAPER = "english_paper"
    STEP_DONE = "done"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="survey_session")
    batch = models.ForeignKey("experiments.ExperimentBatch", on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    language = models.CharField("界面语言", max_length=12, default="zh-hans")
    topic_order_snapshot = models.JSONField("话题初始随机快照", default=list)
    submitted_topic_order = models.JSONField("参与者排序", default=list, blank=True)
    selected_high_topic_id = models.PositiveIntegerField("最高话题 ID", null=True, blank=True)
    selected_low_topic_id = models.PositiveIntegerField("最低话题 ID", null=True, blank=True)
    round_order = models.JSONField("轮次顺序", default=list, blank=True)
    current_session_step = models.CharField("当前会话步骤", max_length=30, default=STEP_TOPIC_ORDER)
    current_round_index = models.PositiveIntegerField("当前轮次序号", default=0)
    batch_snapshot = models.JSONField("批次快照", default=dict)
    step_started_at = models.JSONField("步骤开始时间", default=dict, blank=True)
    step_submitted_at = models.JSONField("步骤提交时间", default=dict, blank=True)
    started_at = models.DateTimeField("开始时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)

    class Meta:
        verbose_name = "答题会话"
        verbose_name_plural = "答题会话"

    def __str__(self):
        return f"{self.user.username} - {self.batch}"


class TopicRound(models.Model):
    HIGH = "high"
    LOW = "low"
    ROUND_TYPES = [(HIGH, "最高话题"), (LOW, "最低话题")]

    session = models.ForeignKey(SurveySession, on_delete=models.CASCADE, related_name="rounds")
    round_type = models.CharField("轮次类型", max_length=10, choices=ROUND_TYPES)
    topic_id = models.PositiveIntegerField("话题 ID")
    material_snapshot = models.JSONField("材料快照", default=dict)
    current_step = models.CharField("当前轮次步骤", max_length=40, default="post")
    step_started_at = models.JSONField("步骤开始时间", default=dict, blank=True)
    step_submitted_at = models.JSONField("步骤提交时间", default=dict, blank=True)
    ai_mode = models.ForeignKey("experiments.AIMode", on_delete=models.SET_NULL, null=True, blank=True)
    skipped_ai = models.BooleanField("跳过 AI", default=False)
    is_completed = models.BooleanField("已完成", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "话题轮次"
        verbose_name_plural = "话题轮次"

    def __str__(self):
        return f"{self.session.user.username} - {self.round_type}"


class CommentReaction(models.Model):
    REACTIONS = [("like", "赞"), ("dislike", "踩"), ("none", "无操作")]

    round = models.ForeignKey(TopicRound, on_delete=models.CASCADE, related_name="comment_reactions")
    comment_snapshot_id = models.PositiveIntegerField("评论快照 ID")
    reaction = models.CharField("反应", max_length=20, choices=REACTIONS, default="none")
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)


class PostReaction(models.Model):
    REACTIONS = CommentReaction.REACTIONS

    round = models.OneToOneField(TopicRound, on_delete=models.CASCADE, related_name="post_reaction")
    reaction = models.CharField("反应", max_length=20, choices=REACTIONS, default="none")
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)


class ScaleResponse(models.Model):
    round = models.ForeignKey(TopicRound, on_delete=models.CASCADE, related_name="scale_responses")
    step = models.CharField("步骤", max_length=40)
    item_type = models.CharField("量表类型", max_length=40)
    item_label = models.CharField("题目文本", max_length=240)
    language = models.CharField("语言", max_length=12)
    min_value = models.IntegerField("最小值", default=1)
    max_value = models.IntegerField("最大值", default=7)
    selected_value = models.IntegerField("选中值")
    elapsed_seconds = models.PositiveIntegerField("用时秒数", default=0)
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)


class TextResponse(models.Model):
    round = models.ForeignKey(TopicRound, on_delete=models.CASCADE, related_name="text_responses")
    step = models.CharField("步骤", max_length=40)
    final_text = models.TextField("最终文本")
    input_method = models.CharField("输入方式", max_length=40, default="keyboard")
    transcribe_model = models.CharField("转写模型", max_length=120, blank=True)
    was_edited = models.BooleanField("是否编辑过", default=False)
    word_count = models.PositiveIntegerField("字数", default=0)
    elapsed_seconds = models.PositiveIntegerField("用时秒数", default=0)
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)


class EnglishPaperResponse(models.Model):
    session = models.OneToOneField(SurveySession, on_delete=models.CASCADE, related_name="english_paper_response")
    prompt = models.TextField("论文要求")
    duration_hours = models.PositiveIntegerField("时长（小时）", default=24)
    paper_text = models.TextField("英文论文")
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True)


class EnglishPaperDraft(models.Model):
    session = models.OneToOneField(SurveySession, on_delete=models.CASCADE, related_name="english_paper_draft")
    prompt = models.TextField("论文要求", blank=True)
    duration_hours = models.PositiveIntegerField("时长（小时）", default=24)
    paper_text = models.TextField("英文论文草稿", blank=True)
    saved_at = models.DateTimeField("暂存时间", auto_now=True)


class ConversationMessage(models.Model):
    ROLES = [("participant", "参与者"), ("assistant", "AI"), ("system", "系统")]

    round = models.ForeignKey(TopicRound, on_delete=models.CASCADE, related_name="conversation_messages")
    role = models.CharField("角色", max_length=20, choices=ROLES)
    content = models.TextField("内容")
    language = models.CharField("语言", max_length=12)
    ai_mode_name = models.CharField("AI 模式", max_length=120, blank=True)
    model_name = models.CharField("模型名称", max_length=120, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    was_interrupted = models.BooleanField("被用户中断", default=False)
    interrupted_at = models.DateTimeField("中断时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)


class QualityEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quality_events")
    session = models.ForeignKey(SurveySession, on_delete=models.SET_NULL, null=True, blank=True, related_name="quality_events")
    event_type = models.CharField("事件类型", max_length=40)
    metadata = models.JSONField("元数据", default=dict, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "质量事件"
        verbose_name_plural = "质量事件"
