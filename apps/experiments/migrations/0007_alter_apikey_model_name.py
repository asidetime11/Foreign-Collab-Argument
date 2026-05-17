from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0006_apikey_model_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apikey",
            name="model_name",
            field=models.TextField(blank=True, verbose_name="支持模型"),
        ),
    ]
