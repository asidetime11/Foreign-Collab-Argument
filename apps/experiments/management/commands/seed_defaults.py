from django.core.management.base import BaseCommand

from apps.experiments.defaults import (
    DEFAULT_AI_MODES,
    DEFAULT_SCALE_ITEMS,
    DEFAULT_TOPICS,
    DEFAULT_TOPIC_ORDER_INTRO_EN,
    DEFAULT_TOPIC_ORDER_INTRO_ZH,
)
from apps.experiments.models import AIMode, ExperimentBatch, RatingScaleConfig, ScaleItem, Topic, TopicComment


OLD_DEMO_INTRO_ZH = "请按你的真实想法对以下话题排序。提交后不可返回修改。"
OLD_DEMO_INTRO_EN = "Please rank the following topics by your own view. You cannot return after submitting."


class Command(BaseCommand):
    help = "Seed local demo batch, topics, scales, and AI modes."

    def handle(self, *args, **options):
        batch, _ = ExperimentBatch.objects.get_or_create(
            name="示例批次 / Demo Batch",
            defaults={
                "intro_zh": DEFAULT_TOPIC_ORDER_INTRO_ZH,
                "intro_en": DEFAULT_TOPIC_ORDER_INTRO_EN,
                "outro_zh": "答题已完成，感谢参与。",
                "outro_en": "The study is complete. Thank you for participating.",
            },
        )
        updates = {}
        if batch.intro_zh in {"", OLD_DEMO_INTRO_ZH}:
            updates["intro_zh"] = DEFAULT_TOPIC_ORDER_INTRO_ZH
        if batch.intro_en in {"", OLD_DEMO_INTRO_EN}:
            updates["intro_en"] = DEFAULT_TOPIC_ORDER_INTRO_EN
        if updates:
            for field, value in updates.items():
                setattr(batch, field, value)
            batch.save(update_fields=list(updates))
        RatingScaleConfig.objects.get_or_create(batch=batch)
        for index, (title_zh, title_en) in enumerate(DEFAULT_TOPICS, start=1):
            topic, _ = Topic.objects.get_or_create(
                title_zh=title_zh,
                position=index,
                defaults={
                    "title_en": title_en,
                    "post_body_zh": f"围绕“{title_zh}”，不同人可能会有不同判断。请阅读下面的评论。",
                    "post_body_en": f"People may judge '{title_en}' differently. Please read the comments below.",
                    "statement_zh": title_zh,
                    "statement_en": title_en,
                },
            )
            topic.batches.add(batch)
            for c_index in range(1, 4):
                TopicComment.objects.get_or_create(
                    topic=topic,
                    position=c_index,
                    defaults={
                        "body_zh": f"这是关于该话题的示例评论 {c_index}。",
                        "body_en": f"This is sample comment {c_index} for the topic.",
                    },
                )
        for index, item in enumerate(DEFAULT_SCALE_ITEMS, start=1):
            item_type, label_zh, label_en = item
            ScaleItem.objects.get_or_create(
                batch=batch,
                item_type=item_type,
                label_zh=label_zh,
                defaults={"label_en": label_en, "position": index},
            )
        for index, mode in enumerate(DEFAULT_AI_MODES, start=1):
            AIMode.objects.get_or_create(
                batch=batch,
                name_zh=mode["name_zh"],
                defaults={**mode, "position": index},
            )
        self.stdout.write(self.style.SUCCESS("Demo defaults seeded."))
