from django.db import migrations


def fill_defaults(apps, schema_editor):
    Topic = apps.get_model("experiments", "Topic")
    for topic in Topic.objects.all():
        changed = []
        if not topic.agreement_prompt_zh:
            statement = topic.statement_zh or topic.title_zh
            if statement:
                topic.agreement_prompt_zh = f'你有多大程度上同意"{statement}"这个观点？'
            else:
                topic.agreement_prompt_zh = "你有多大程度上同意这个观点？"
            changed.append("agreement_prompt_zh")
        if not topic.confidence_prompt_zh:
            topic.confidence_prompt_zh = "你对自己上述的观点有多确定？"
            changed.append("confidence_prompt_zh")
        if changed:
            topic.save(update_fields=changed)


def clear_defaults(apps, schema_editor):
    Topic = apps.get_model("experiments", "Topic")
    Topic.objects.update(
        agreement_prompt_zh="",
        confidence_prompt_zh="",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("experiments", "0009_topic_stance_prompts"),
    ]

    operations = [
        migrations.RunPython(fill_defaults, clear_defaults),
    ]
