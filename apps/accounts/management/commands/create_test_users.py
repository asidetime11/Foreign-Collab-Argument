from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.experiments.models import ExperimentBatch


TEST_USERS = ["tester1", "tester2"]


class Command(BaseCommand):
    help = "创建或更新团队测试账号（tester1 / tester2），标记为测试账号，可在后台一键重置答题记录。"

    def add_arguments(self, parser):
        parser.add_argument("--password", default="test1234", help="测试账号密码（默认 test1234）")
        parser.add_argument("--batch", type=int, metavar="BATCH_ID", help="绑定到指定批次 ID")

    def handle(self, *args, **options):
        password = options["password"]
        batch_id = options["batch"]
        batch = None
        if batch_id:
            try:
                batch = ExperimentBatch.objects.get(pk=batch_id)
            except ExperimentBatch.DoesNotExist:
                raise CommandError(f"批次 ID={batch_id} 不存在。")

        for username in TEST_USERS:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.is_staff = False
            user.is_superuser = False
            user.save()
            profile = user.participant_profile
            profile.is_tester = True
            if batch:
                profile.batch = batch
            profile.save(update_fields=["is_tester", "batch", "updated_at"] if batch else ["is_tester", "updated_at"])
            action = "已创建" if created else "已更新"
            batch_hint = f"，绑定批次「{batch.name}」" if batch else ""
            self.stdout.write(self.style.SUCCESS(f"{action} 测试账号：{username}（密码：{password}）{batch_hint}"))

        self.stdout.write("\n测试账号已就绪。在「用户数据」页可对其使用「重置记录」按钮。")
