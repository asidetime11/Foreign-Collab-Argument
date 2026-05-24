from django.db import migrations, models


AGREEMENT_DEFAULTS = ["非常不同意", "不同意", "有点不同意", "有点同意", "同意", "非常同意"]
CONFIDENCE_DEFAULTS = ["完全不确定", "不确定", "有点不确定", "有点确定", "确定", "非常确定"]


def fill_defaults(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    for batch in ExperimentBatch.objects.all():
        changed = []
        for i, value in enumerate(AGREEMENT_DEFAULTS, start=1):
            field = f"agreement_label_{i}"
            if not getattr(batch, field):
                setattr(batch, field, value)
                changed.append(field)
        for i, value in enumerate(CONFIDENCE_DEFAULTS, start=1):
            field = f"confidence_label_{i}"
            if not getattr(batch, field):
                setattr(batch, field, value)
                changed.append(field)
        if changed:
            batch.save(update_fields=changed)


def clear_defaults(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    for i in range(1, 7):
        ExperimentBatch.objects.update(**{f"agreement_label_{i}": "", f"confidence_label_{i}": ""})


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0010_topic_stance_prompts_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_1",
            field=models.CharField(blank=True, default="非常不同意", max_length=60, verbose_name="同意度刻度 1"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_2",
            field=models.CharField(blank=True, default="不同意", max_length=60, verbose_name="同意度刻度 2"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_3",
            field=models.CharField(blank=True, default="有点不同意", max_length=60, verbose_name="同意度刻度 3"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_4",
            field=models.CharField(blank=True, default="有点同意", max_length=60, verbose_name="同意度刻度 4"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_5",
            field=models.CharField(blank=True, default="同意", max_length=60, verbose_name="同意度刻度 5"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="agreement_label_6",
            field=models.CharField(blank=True, default="非常同意", max_length=60, verbose_name="同意度刻度 6"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_1",
            field=models.CharField(blank=True, default="完全不确定", max_length=60, verbose_name="确定度刻度 1"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_2",
            field=models.CharField(blank=True, default="不确定", max_length=60, verbose_name="确定度刻度 2"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_3",
            field=models.CharField(blank=True, default="有点不确定", max_length=60, verbose_name="确定度刻度 3"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_4",
            field=models.CharField(blank=True, default="有点确定", max_length=60, verbose_name="确定度刻度 4"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_5",
            field=models.CharField(blank=True, default="确定", max_length=60, verbose_name="确定度刻度 5"),
        ),
        migrations.AddField(
            model_name="experimentbatch",
            name="confidence_label_6",
            field=models.CharField(blank=True, default="非常确定", max_length=60, verbose_name="确定度刻度 6"),
        ),
        migrations.RunPython(fill_defaults, clear_defaults),
    ]
