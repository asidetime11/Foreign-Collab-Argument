from django.core.management import call_command
from django.test import TestCase

from .models import AIMode, ExperimentBatch, ScaleItem, Topic, TopicComment


class ExperimentModelTests(TestCase):
    def test_batch_defaults_match_design(self):
        batch = ExperimentBatch.objects.create(name="批次 A")

        self.assertEqual(batch.ai_chat_minutes, 5)
        self.assertEqual(batch.ai_neutrality, ExperimentBatch.NEUTRALITY_MODERATE)
        self.assertEqual(batch.topic_selection_strategy, ExperimentBatch.TOPIC_STRATEGY_HIGHEST_LOWEST)
        self.assertEqual(batch.round_order_strategy, ExperimentBatch.ROUND_RANDOM)

    def test_comment_presentation_is_generated(self):
        batch = ExperimentBatch.objects.create(name="批次 A")
        topic = Topic.objects.create(batch=batch, title_zh="话题", position=1)

        comment = TopicComment.objects.create(topic=topic, body_zh="这是评论", position=1)

        self.assertTrue(comment.auto_author_name)
        self.assertTrue(comment.avatar_seed)
        self.assertTrue(comment.relative_time)

    def test_seed_defaults_is_idempotent(self):
        call_command("seed_defaults")
        call_command("seed_defaults")

        batch = ExperimentBatch.objects.get(name__contains="Demo Batch")
        self.assertEqual(Topic.objects.filter(batch=batch).count(), 10)
        self.assertEqual(AIMode.objects.filter(batch=batch).count(), 3)
        self.assertEqual(ScaleItem.objects.filter(batch=batch).count(), 4)
