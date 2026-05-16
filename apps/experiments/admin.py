from django import forms
from django.contrib import admin
from django.db import models

from .admin_views import default_batch
from .models import AIMode, Topic, TopicComment


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


@admin.register(AIMode)
class AIModeAdmin(admin.ModelAdmin):
    list_display = ("name_zh", "is_enabled", "position")
    list_filter = ("is_enabled",)
    search_fields = ("name_zh", "prompt_zh")
    fieldsets = (
        ("模式", {"fields": ("name_zh", "name_en", "is_enabled", "position")}),
        ("Prompt", {"fields": ("prompt_zh", "prompt_en")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.batch_id:
            obj.batch = default_batch()
        super().save_model(request, obj, form, change)
