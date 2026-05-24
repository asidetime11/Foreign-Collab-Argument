import django.db.models.deletion
from django.db import migrations, models


def create_configs_for_existing_batches(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    EnglishPaperConfig = apps.get_model("experiments", "EnglishPaperConfig")
    for batch in ExperimentBatch.objects.all():
        EnglishPaperConfig.objects.get_or_create(
            batch=batch,
            defaults={
                "title_zh": "英文论文写作",
                "title_en": "English paper writing",
                "intro_zh": "请在规定时间内完成英文论文写作。",
                "intro_en": "Please complete your English argumentative essay within the time limit.",
                "prompt": batch.english_paper_prompt or "Write an English argumentative essay based on the discussion you completed.",
                "duration_minutes": 30,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0017_add_aimode_intro_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnglishPaperConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_zh", models.CharField(default="英文论文写作", max_length=200, verbose_name="标题（中文）")),
                ("title_en", models.CharField(default="English paper writing", max_length=200, verbose_name="标题（英文）")),
                ("intro_zh", models.TextField(blank=True, default="请在规定时间内完成英文论文写作。", help_text="显示在标题下方的引导说明。", verbose_name="说明文字（中文）")),
                ("intro_en", models.TextField(blank=True, default="Please complete your English argumentative essay within the time limit.", verbose_name="说明文字（英文）")),
                ("prompt", models.TextField(default="Write an English argumentative essay based on the discussion you completed.", verbose_name="英文论文要求")),
                ("duration_minutes", models.PositiveIntegerField(default=30, verbose_name="时长（分钟）")),
                ("batch", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="english_paper_config", to="experiments.experimentbatch", verbose_name="实验批次")),
            ],
            options={
                "verbose_name": "英文论文配置",
                "verbose_name_plural": "英文论文配置",
            },
        ),
        migrations.RunPython(create_configs_for_existing_batches, migrations.RunPython.noop),
    ]
