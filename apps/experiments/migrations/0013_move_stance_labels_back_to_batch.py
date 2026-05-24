from django.db import migrations, models


def copy_topic_labels_back_to_batch(apps, schema_editor):
    ExperimentBatch = apps.get_model("experiments", "ExperimentBatch")
    for batch in ExperimentBatch.objects.prefetch_related("topics").all():
        source = batch.topics.order_by("id").first()
        if not source:
            continue
        changed = []
        for i in range(1, 7):
            for prefix in ("agreement_label_", "confidence_label_"):
                field = f"{prefix}{i}"
                value = getattr(source, field, "")
                if value and getattr(batch, field) != value:
                    setattr(batch, field, value)
                    changed.append(field)
        if changed:
            batch.save(update_fields=changed)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0012_move_stance_labels_to_topic"),
    ]

    operations = [
        # 1. Re-add fields on ExperimentBatch
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
        # 2. Copy from topic to batch
        migrations.RunPython(copy_topic_labels_back_to_batch, noop),
        # 3. Drop Topic columns
        migrations.RemoveField(model_name="topic", name="agreement_label_1"),
        migrations.RemoveField(model_name="topic", name="agreement_label_2"),
        migrations.RemoveField(model_name="topic", name="agreement_label_3"),
        migrations.RemoveField(model_name="topic", name="agreement_label_4"),
        migrations.RemoveField(model_name="topic", name="agreement_label_5"),
        migrations.RemoveField(model_name="topic", name="agreement_label_6"),
        migrations.RemoveField(model_name="topic", name="confidence_label_1"),
        migrations.RemoveField(model_name="topic", name="confidence_label_2"),
        migrations.RemoveField(model_name="topic", name="confidence_label_3"),
        migrations.RemoveField(model_name="topic", name="confidence_label_4"),
        migrations.RemoveField(model_name="topic", name="confidence_label_5"),
        migrations.RemoveField(model_name="topic", name="confidence_label_6"),
    ]
