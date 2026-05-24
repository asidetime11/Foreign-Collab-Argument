# Generated migration
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_participantprofile_batch"),
    ]
    operations = [
        migrations.AddField(
            model_name="participantprofile",
            name="is_tester",
            field=models.BooleanField(default=False, help_text="测试账号可在后台一键重置答题记录，不计入正式数据。", verbose_name="测试账号"),
        ),
    ]
