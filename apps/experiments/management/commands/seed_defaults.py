from django.core.management.base import BaseCommand

from apps.experiments.defaults import (
    DEFAULT_AI_MODES,
    DEFAULT_SCALE_ITEMS,
    DEFAULT_TOPICS,
    DEFAULT_TOPIC_ORDER_INTRO_EN,
    DEFAULT_TOPIC_ORDER_INTRO_ZH,
)
from apps.experiments.models import AIMode, EnglishPaperConfig, ExperimentBatch, RatingScaleConfig, ScaleItem, Topic, TopicComment


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
        ep_config, ep_created = EnglishPaperConfig.objects.get_or_create(
            batch=batch,
            defaults={
                "title_zh": "英文论文写作",
                "title_en": "English paper writing",
                "intro_zh": "请在规定时间内完成英文论文写作。",
                "intro_en": "Please complete your English argumentative essay within the time limit.",
                "prompt": "Write an English argumentative essay based on the discussion you completed.",
                "duration_minutes": 30,
                "gate_title_zh": "即将进入写作模块",
                "gate_title_en": "You're About to Enter the Writing Module",
                "gate_body_zh": '接下来你将进行英文论文写作。请放轻松，根据你对话题的理解，用英文写一篇论证性短文。计时将在你点击"进入写作"后开始。',
                "gate_body_en": 'You will now write a short argumentative essay in English. Take a deep breath and relax. The timer will start after you click "Start Writing".',
                "gate_cta_zh": "进入写作",
                "gate_cta_en": "Start Writing",
            },
        )
        if not ep_created and ep_config.duration_minutes != 30 and ep_config.duration_minutes == 0:
            ep_config.duration_minutes = 30
            ep_config.save(update_fields=["duration_minutes"])
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
        scale_types = {item[0] for item in DEFAULT_SCALE_ITEMS}
        ScaleItem.objects.filter(batch=batch, item_type__in=scale_types).delete()
        for index, item in enumerate(DEFAULT_SCALE_ITEMS, start=1):
            item_type, label_zh, label_en, min_value, max_value = item
            ScaleItem.objects.create(
                batch=batch,
                item_type=item_type,
                label_zh=label_zh,
                label_en=label_en,
                position=index,
                min_value=min_value,
                max_value=max_value,
            )
        for index, mode in enumerate(DEFAULT_AI_MODES, start=1):
            obj, created = AIMode.objects.get_or_create(
                batch=batch,
                name_zh=mode["name_zh"],
                defaults={**mode, "position": index},
            )
            if not created and not obj.intro_template_zh:
                obj.intro_template_zh = mode.get("intro_template_zh", "")
                obj.intro_template_en = mode.get("intro_template_en", "")
                obj.save(update_fields=["intro_template_zh", "intro_template_en"])
        self.stdout.write(self.style.SUCCESS("Demo defaults seeded."))
