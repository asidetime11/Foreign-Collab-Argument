from django.contrib import admin

from .models import CommentReaction, ConversationMessage, QualityEvent, ScaleResponse, SurveySession, TextResponse, TopicRound


class TopicRoundInline(admin.TabularInline):
    model = TopicRound
    extra = 0


@admin.register(SurveySession)
class SurveySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "batch", "current_session_step", "current_round_index", "started_at", "completed_at")
    list_filter = ("batch", "current_session_step")
    inlines = [TopicRoundInline]


admin.site.register(CommentReaction)
admin.site.register(ScaleResponse)
admin.site.register(TextResponse)
admin.site.register(ConversationMessage)
admin.site.register(QualityEvent)
