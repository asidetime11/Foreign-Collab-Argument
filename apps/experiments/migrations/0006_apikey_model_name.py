from django.db import migrations, models


def copy_provider_model_to_keys(apps, schema_editor):
    APIKey = apps.get_model("experiments", "APIKey")
    for key in APIKey.objects.select_related("provider"):
        if not key.model_name and key.provider_id:
            key.model_name = key.provider.model_name
            key.save(update_fields=["model_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0005_llmprovider_priority"),
    ]

    operations = [
        migrations.AddField(
            model_name="apikey",
            name="model_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="模型"),
        ),
        migrations.RunPython(copy_provider_model_to_keys, migrations.RunPython.noop),
    ]
