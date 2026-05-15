from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import AIMode, ExperimentBatch, RatingScaleConfig, ScaleItem, Topic, TopicComment


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0


class TopicCommentInline(admin.TabularInline):
    model = TopicComment
    extra = 0
    readonly_fields = ("auto_author_name", "avatar_seed", "like_count", "relative_time")


@admin.register(ExperimentBatch)
class ExperimentBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "ai_chat_minutes", "ai_neutrality", "export_link")
    list_filter = ("is_active", "ai_neutrality")
    search_fields = ("name",)
    inlines = [TopicInline]

    def export_link(self, obj):
        if not obj.pk:
            return ""
        url = reverse("exports:batch_export", args=[obj.pk])
        return format_html('<a class="button" href="{}">导出数据</a>', url)

    export_link.short_description = "批次导出"


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title_zh", "batch", "is_enabled", "position")
    list_filter = ("batch", "is_enabled")
    search_fields = ("title_zh", "title_en")
    inlines = [TopicCommentInline]


@admin.register(ScaleItem)
class ScaleItemAdmin(admin.ModelAdmin):
    list_display = ("label_zh", "batch", "item_type", "position")
    list_filter = ("batch", "item_type")


admin.site.register(RatingScaleConfig)
admin.site.register(AIMode)
