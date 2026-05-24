from django.core.management.base import BaseCommand, CommandError

from apps.experiments.models import ExperimentBatch
from apps.survey.models import SurveySession, TopicRound
from apps.survey.services import _topic_snapshots


class Command(BaseCommand):
    help = "刷新指定批次中所有未完成 session 的话题快照（topic_order_snapshot 与 material_snapshot）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=int,
            metavar="BATCH_ID",
            help="批次 ID（留空则列出所有批次）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预览，不实际修改",
        )

    def handle(self, *args, **options):
        batch_id = options["batch"]
        dry_run = options["dry_run"]

        if not batch_id:
            batches = ExperimentBatch.objects.order_by("id")
            if not batches.exists():
                raise CommandError("数据库中没有任何批次。")
            self.stdout.write("可用批次：")
            for b in batches:
                count = SurveySession.objects.filter(batch=b).exclude(current_session_step="done").count()
                self.stdout.write(f"  ID={b.pk}  {b.name}  （未完成 session: {count}）")
            self.stdout.write("\n请用 --batch <ID> 指定要刷新的批次。")
            return

        try:
            batch = ExperimentBatch.objects.get(pk=batch_id)
        except ExperimentBatch.DoesNotExist:
            raise CommandError(f"批次 ID={batch_id} 不存在。")

        sessions = (
            SurveySession.objects.filter(batch=batch)
            .exclude(current_session_step="done")
            .prefetch_related("rounds")
        )

        if not sessions.exists():
            self.stdout.write(self.style.WARNING(f"批次「{batch.name}」没有未完成的 session，无需刷新。"))
            return

        # 用当前数据库内容构建最新快照（按 id 索引）
        new_snapshots = _topic_snapshots.__wrapped__(batch) if hasattr(_topic_snapshots, "__wrapped__") else _build_snapshots(batch)
        snapshot_by_id = {item["id"]: item for item in new_snapshots}

        session_count = 0
        round_count = 0

        for session in sessions:
            # 1. 刷新 topic_order_snapshot（保留顺序，只更新内容）
            updated_order = []
            for item in session.topic_order_snapshot:
                tid = item["id"]
                updated_order.append(snapshot_by_id.get(tid, item))
            # 把快照中已不存在的话题也加进来（新增话题）
            existing_ids = {item["id"] for item in session.topic_order_snapshot}
            for tid, snap in snapshot_by_id.items():
                if tid not in existing_ids:
                    updated_order.append(snap)

            if not dry_run:
                session.topic_order_snapshot = updated_order
                session.save(update_fields=["topic_order_snapshot"])
            session_count += 1

            # 2. 刷新未完成 round 的 material_snapshot
            for round_obj in session.rounds.all():
                if round_obj.is_completed:
                    continue
                tid = round_obj.topic_id
                if tid in snapshot_by_id:
                    if not dry_run:
                        round_obj.material_snapshot = snapshot_by_id[tid]
                        round_obj.save(update_fields=["material_snapshot"])
                    round_count += 1

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}批次「{batch.name}」：已刷新 {session_count} 个 session 的 topic_order_snapshot，"
                f"{round_count} 个未完成 round 的 material_snapshot。"
            )
        )


def _build_snapshots(batch):
    """不打乱顺序地构建最新快照列表。"""
    return [
        topic.snapshot()
        for topic in batch.topics.filter(is_enabled=True).prefetch_related("comments")
    ]
