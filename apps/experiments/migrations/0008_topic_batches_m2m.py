from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    Topic = apps.get_model("experiments", "Topic")
    for topic in Topic.objects.all():
        if topic.batch_id:
            topic.batches.add(topic.batch_id)


def copy_m2m_to_fk(apps, schema_editor):
    Topic = apps.get_model("experiments", "Topic")
    for topic in Topic.objects.all():
        first = topic.batches.order_by("id").first()
        if first:
            topic.batch_id = first.pk
            topic.save(update_fields=["batch"])


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0007_alter_apikey_model_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="topic",
            name="batches",
            field=models.ManyToManyField(
                blank=True,
                help_text="一个话题可以同时属于多个批次。",
                related_name="topics_m2m_tmp",
                to="experiments.experimentbatch",
                verbose_name="所属批次",
            ),
        ),
        migrations.RunPython(copy_fk_to_m2m, copy_m2m_to_fk),
        migrations.RemoveField(
            model_name="topic",
            name="batch",
        ),
        migrations.AlterField(
            model_name="topic",
            name="batches",
            field=models.ManyToManyField(
                blank=True,
                help_text="一个话题可以同时属于多个批次。",
                related_name="topics",
                to="experiments.experimentbatch",
                verbose_name="所属批次",
            ),
        ),
    ]
