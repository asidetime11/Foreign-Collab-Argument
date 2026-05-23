from django.db import migrations, models


AGREEMENT_DEFAULTS = ["非常不同意", "不同意", "有点不同意", "有点同意", "同意", "非常同意"]
CONFIDENCE_DEFAULTS = ["完全不确定", "不确定", "有点不确定", "有点确定", "确定", "非常确定"]


def copy_labels_to_topics(apps, schema_editor):
    Topic = apps.get_model("experiments", "Topic")
    for topic in Topic.objects.prefetch_related("batches").all():
        source = topic.batches.order_by("id").first()
        changed = []
        for i in range(1, 7):
            agree_field = f"agreement_label_{i}"
            conf_field = f"confidence_label_{i}"
            if not getattr(topic, agree_field):
                value = getattr(source, agree_field, "") if source else ""
                setattr(topic, agree_field, value or AGREEMENT_DEFAULTS[i - 1])
                changed.append(agree_field)
            if not getattr(topic, conf_field):
                value = getattr(source, conf_field, "") if source else ""
                setattr(topic, conf_field, value or CONFIDENCE_DEFAULTS[i - 1])
                changed.append(conf_field)
        if changed:
            topic.save(update_fields=changed)


def copy_labels_back_to_batches(apps, schema_editor):
    # Reverse migration: nothing to do since the batch fields are being recreated
    # by the reverse of the RemoveField operation; values will use field defaults.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0011_experimentbatch_stance_labels"),
    ]

    operations = [
        # 1. Add fields to Topic
        migrations.AddField(
            model_name="topic",
            name="agreement_label_1",
            field=models.CharField(blank=True, default="非常不同意", max_length=60, verbose_name="同意度刻度 1"),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_label_2",
            field=models.CharField(blank=True, default="不同意", max_length=60, verbose_name="同意度刻度 2"),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_label_3",
            field=models.CharField(blank=True, default="有点不同意", max_length=60, verbose_name="同意度刻度 3"),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_label_4",
            field=models.CharField(blank=True, default="有点同意", max_length=60, verbose_name="同意度刻度 4"),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_label_5",
            field=models.CharField(blank=True, default="同意", max_length=60, verbose_name="同意度刻度 5"),
        ),
        migrations.AddField(
            model_name="topic",
            name="agreement_label_6",
            field=models.CharField(blank=True, default="非常同意", max_length=60, verbose_name="同意度刻度 6"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_1",
            field=models.CharField(blank=True, default="完全不确定", max_length=60, verbose_name="确定度刻度 1"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_2",
            field=models.CharField(blank=True, default="不确定", max_length=60, verbose_name="确定度刻度 2"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_3",
            field=models.CharField(blank=True, default="有点不确定", max_length=60, verbose_name="确定度刻度 3"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_4",
            field=models.CharField(blank=True, default="有点确定", max_length=60, verbose_name="确定度刻度 4"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_5",
            field=models.CharField(blank=True, default="确定", max_length=60, verbose_name="确定度刻度 5"),
        ),
        migrations.AddField(
            model_name="topic",
            name="confidence_label_6",
            field=models.CharField(blank=True, default="非常确定", max_length=60, verbose_name="确定度刻度 6"),
        ),
        # 2. Copy data from batch to topic
        migrations.RunPython(copy_labels_to_topics, copy_labels_back_to_batches),
        # 3. Remove the batch-level fields
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_1"),
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_2"),
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_3"),
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_4"),
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_5"),
        migrations.RemoveField(model_name="experimentbatch", name="agreement_label_6"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_1"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_2"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_3"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_4"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_5"),
        migrations.RemoveField(model_name="experimentbatch", name="confidence_label_6"),
    ]
