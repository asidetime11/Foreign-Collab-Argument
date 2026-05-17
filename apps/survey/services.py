import random

from django.utils import timezone

from apps.experiments.models import ExperimentBatch, ScaleItem, Topic

from .models import QualityEvent, SurveySession, TopicRound


STEP_TOPIC_ORDER = "topic_order"
ROUND_STEPS = ["post", "emotion", "stance_before", "initial_text", "mode", "chat", "ai_eval", "stance_after", "final_text"]
SESSION_DONE = "done"


def get_or_create_session(user, language="zh-hans"):
    profile = user.participant_profile
    if not profile.batch:
        raise ValueError("missing_batch")
    session, created = SurveySession.objects.get_or_create(
        user=user,
        defaults={
            "batch": profile.batch,
            "language": language,
            "batch_snapshot": _batch_snapshot(profile.batch),
            "topic_order_snapshot": _topic_snapshots(profile.batch),
        },
    )
    if session.language != "zh-hans":
        session.language = "zh-hans"
        session.save(update_fields=["language"])
    return session


def _batch_snapshot(batch: ExperimentBatch):
    return {
        "id": batch.pk,
        "name": batch.name,
        "intro_zh": batch.intro_zh,
        "intro_en": batch.intro_en,
        "outro_zh": batch.outro_zh,
        "outro_en": batch.outro_en,
        "ai_chat_minutes": batch.ai_chat_minutes,
        "ai_neutrality": batch.ai_neutrality,
        "english_paper_prompt": batch.english_paper_prompt,
        "english_paper_duration_hours": batch.english_paper_duration_hours,
    }


def _topic_snapshots(batch: ExperimentBatch):
    topics = [topic.snapshot() for topic in batch.topics.filter(is_enabled=True).prefetch_related("comments")]
    random.shuffle(topics)
    return topics


def submit_topic_order(session: SurveySession, ordered_topic_ids):
    if session.current_session_step != STEP_TOPIC_ORDER or session.submitted_topic_order:
        raise PermissionError("topic order already submitted")
    ids = [int(value) for value in ordered_topic_ids]
    if len(ids) < 2:
        raise ValueError("at least two topics are required")
    snapshot_by_id = {int(item["id"]): item for item in session.topic_order_snapshot}
    if set(ids) != set(snapshot_by_id):
        raise ValueError("topic ids do not match snapshot")

    high_id = ids[0]
    low_id = ids[-1]
    round_order = [TopicRound.HIGH, TopicRound.LOW]
    random.shuffle(round_order)
    session.submitted_topic_order = ids
    session.selected_high_topic_id = high_id
    session.selected_low_topic_id = low_id
    session.round_order = round_order
    session.current_session_step = SurveySession.STEP_ROUND
    session.save()

    topic_ids = {TopicRound.HIGH: high_id, TopicRound.LOW: low_id}
    for round_type in round_order:
        TopicRound.objects.create(
            session=session,
            round_type=round_type,
            topic_id=topic_ids[round_type],
            material_snapshot=snapshot_by_id[topic_ids[round_type]],
        )
    return session


def current_round(session: SurveySession):
    if session.current_session_step != SurveySession.STEP_ROUND:
        return None
    rounds = list(session.rounds.all())
    if session.current_round_index >= len(rounds):
        return None
    return rounds[session.current_round_index]


def current_step(session: SurveySession):
    if session.current_session_step == SurveySession.STEP_DONE:
        return SESSION_DONE
    if session.current_session_step == SurveySession.STEP_ENGLISH_PAPER:
        return SurveySession.STEP_ENGLISH_PAPER
    if session.current_session_step == STEP_TOPIC_ORDER:
        return STEP_TOPIC_ORDER
    round_obj = current_round(session)
    return round_obj.current_step if round_obj else SESSION_DONE


def start_current_step(session: SurveySession):
    now = timezone.now().isoformat()
    if session.current_session_step == STEP_TOPIC_ORDER:
        session.step_started_at.setdefault(STEP_TOPIC_ORDER, now)
        session.save(update_fields=["step_started_at"])
        return
    if session.current_session_step == SurveySession.STEP_ENGLISH_PAPER:
        session.step_started_at.setdefault(SurveySession.STEP_ENGLISH_PAPER, now)
        session.save(update_fields=["step_started_at"])
        return
    round_obj = current_round(session)
    if round_obj:
        round_obj.step_started_at.setdefault(round_obj.current_step, now)
        round_obj.save(update_fields=["step_started_at"])


def complete_round_step(round_obj: TopicRound, step):
    if round_obj.current_step != step or round_obj.is_completed:
        raise PermissionError("step is not current")
    round_obj.step_submitted_at[step] = timezone.now().isoformat()
    index = ROUND_STEPS.index(step)
    if step == "final_text":
        _complete_round(round_obj)
        return
    round_obj.current_step = ROUND_STEPS[index + 1]
    round_obj.save()


def advance_after_mode(round_obj: TopicRound, selected_mode_or_skip):
    if round_obj.current_step != "mode":
        raise PermissionError("mode is not current")
    round_obj.step_submitted_at["mode"] = timezone.now().isoformat()
    if selected_mode_or_skip == "skip":
        round_obj.skipped_ai = True
        round_obj.current_step = "stance_after"
    else:
        round_obj.ai_mode_id = int(selected_mode_or_skip)
        round_obj.current_step = "chat"
    round_obj.save()


def _complete_round(round_obj: TopicRound):
    round_obj.is_completed = True
    round_obj.save()
    session = round_obj.session
    next_index = session.current_round_index + 1
    if next_index >= session.rounds.count():
        session.current_session_step = SurveySession.STEP_ENGLISH_PAPER
    else:
        session.current_round_index = next_index
    session.save()


def complete_english_paper(session: SurveySession):
    session.current_session_step = SurveySession.STEP_DONE
    session.completed_at = timezone.now()
    session.save(update_fields=["current_session_step", "completed_at"])


def scale_items_for_step(batch, step):
    mapping = {
        "emotion": ScaleItem.EMOTION,
        "ai_eval": ScaleItem.AI_EVAL,
        "stance_before": ScaleItem.STANCE,
        "stance_after": ScaleItem.STANCE,
    }
    item_type = mapping.get(step)
    return batch.scale_items.filter(item_type=item_type) if item_type else []


def record_quality_event(user, event_type, metadata=None):
    session = getattr(user, "survey_session", None)
    return QualityEvent.objects.create(
        user=user,
        session=session,
        event_type=event_type,
        metadata=metadata or {},
    )
