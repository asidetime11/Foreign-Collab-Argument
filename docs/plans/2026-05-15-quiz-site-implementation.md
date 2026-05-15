# Quiz Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django-based research quiz website with fixed participant flow, bilingual materials, AI chat, speech-to-text input, step locking, Chinese admin, and selectable batch exports.

**Architecture:** Use a Django monolith with focused apps for accounts, experiment configuration, survey flow, AI services, and exports. Server-side state controls every allowed step; browser JavaScript only improves interaction and never becomes the source of truth. Participant-visible content is snapshotted when a survey session starts so later admin edits do not change historical data.

**Tech Stack:** Python 3.12, Django 5.x, PostgreSQL-ready settings with SQLite for local development, pytest-django, OpenAI-compatible client for Dubrify, openpyxl, vanilla JavaScript, Django templates, Django admin.

---

## Source Spec

Implementation follows `docs/superpowers/specs/2026-05-15-quiz-site-design.md`.

## File Structure

Create this structure:

```text
manage.py
pyproject.toml
.env.example
config/
  __init__.py
  settings.py
  urls.py
  asgi.py
  wsgi.py
apps/
  __init__.py
  accounts/
    __init__.py
    admin.py
    apps.py
    forms.py
    models.py
    tests.py
    urls.py
    views.py
  experiments/
    __init__.py
    admin.py
    apps.py
    defaults.py
    models.py
    services.py
    tests.py
  survey/
    __init__.py
    admin.py
    apps.py
    forms.py
    models.py
    services.py
    tests.py
    urls.py
    views.py
  ai/
    __init__.py
    apps.py
    clients.py
    prompts.py
    tests.py
    urls.py
    views.py
  exports/
    __init__.py
    apps.py
    services.py
    tests.py
    urls.py
    views.py
templates/
  base.html
  registration/login.html
  accounts/profile_prompt.html
  accounts/profile.html
  survey/layout.html
  survey/start.html
  survey/step_topic_order.html
  survey/step_post.html
  survey/step_scale.html
  survey/step_text.html
  survey/step_mode.html
  survey/step_chat.html
  survey/done.html
static/
  survey/css/site.css
  survey/js/quality-events.js
  survey/js/topic-order.js
  survey/js/rating.js
  survey/js/recorder.js
  survey/js/chat.js
```

Responsibilities:

- `apps.experiments`: admin-configured batches, topics, comments, scale items, AI modes, default seed data.
- `apps.accounts`: participant profile, first-login nickname prompt, profile edit page, admin bulk account creation.
- `apps.survey`: session state machine, snapshots, participant-facing steps, responses, quality events.
- `apps.ai`: Dubrify/OpenAI-compatible chat and transcription clients, prompt composition, streaming endpoints.
- `apps.exports`: batch export selection, Excel workbook generation, CSV zip generation.

## Task 1: Bootstrap Django Project

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `manage.py`
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: empty `__init__.py` files under `config/` and `apps/`
- Create: each app `apps.py`

- [ ] **Step 1: Create dependency manifest**

Create `pyproject.toml` with:

```toml
[project]
name = "foreign-collab-argument"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "django>=5.0,<6.0",
  "psycopg[binary]>=3.1",
  "python-dotenv>=1.0",
  "openai>=1.30",
  "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-django>=4.8",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
```

- [ ] **Step 2: Install dependencies**

Run: `python -m pip install -e .[dev]`

Expected: Django, pytest-django, OpenAI client, and openpyxl install successfully.

- [ ] **Step 3: Create settings**

Create `config/settings.py` with environment-based settings:

```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.experiments",
    "apps.survey",
    "apps.ai",
    "apps.exports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

LANGUAGE_CODE = "zh-hans"
LANGUAGES = [("zh-hans", "中文"), ("en", "English")]
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "survey:start"
LOGOUT_REDIRECT_URL = "login"

DUBRIFY_BASE_URL = os.getenv("DUBRIFY_BASE_URL", "https://api.dubrify.com/v1")
DUBRIFY_API_KEY = os.getenv("DUBRIFY_API_KEY", "")
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "deepseek-r1")
DEFAULT_TRANSCRIBE_MODEL = os.getenv("DEFAULT_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
```

- [ ] **Step 4: Create URL root**

Create `config/urls.py` with admin, auth, app URL includes, and language switching:

```python
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("profile/", include("apps.accounts.urls")),
    path("survey/", include("apps.survey.urls")),
    path("ai/", include("apps.ai.urls")),
    path("exports/", include("apps.exports.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", RedirectView.as_view(pattern_name="survey:start", permanent=False)),
]
```

- [ ] **Step 5: Verify project starts**

Run: `python manage.py check`

Expected: `System check identified no issues`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example manage.py config apps
git commit -m "chore: bootstrap django project"
```

## Task 2: Accounts and Participant Profiles

**Files:**
- Create: `apps/accounts/models.py`
- Create: `apps/accounts/forms.py`
- Create: `apps/accounts/views.py`
- Create: `apps/accounts/urls.py`
- Create: `apps/accounts/admin.py`
- Create: `templates/registration/login.html`
- Create: `templates/accounts/profile_prompt.html`
- Create: `templates/accounts/profile.html`
- Test: `apps/accounts/tests.py`

- [ ] **Step 1: Write profile model test**

In `apps/accounts/tests.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from apps.accounts.models import ParticipantProfile


class ParticipantProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="p001", password="pass")
        profile = ParticipantProfile.objects.get(user=user)
        self.assertEqual(profile.display_name, "")
        self.assertFalse(profile.has_required_display_name)
```

- [ ] **Step 2: Run failing test**

Run: `python manage.py test apps.accounts`

Expected: FAIL because `ParticipantProfile` does not exist.

- [ ] **Step 3: Create profile model and signal**

In `apps/accounts/models.py`:

```python
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class ParticipantProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participant_profile")
    display_name = models.CharField("称呼/姓名", max_length=120, blank=True)
    region = models.CharField("地区", max_length=120, blank=True)
    age_range = models.CharField("年龄段", max_length=50, blank=True)
    gender = models.CharField("性别", max_length=50, blank=True)
    organization_type = models.CharField("学校/单位类型", max_length=120, blank=True)
    education_or_work = models.CharField("教育阶段/职业状态", max_length=120, blank=True)
    contact = models.CharField("联系方式", max_length=120, blank=True)
    notes = models.TextField("备注", blank=True)
    batch = models.ForeignKey("experiments.ExperimentBatch", on_delete=models.PROTECT, null=True, blank=True, related_name="participants")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "参与者资料"
        verbose_name_plural = "参与者资料"

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def has_required_display_name(self):
        return bool(self.display_name.strip())


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_participant_profile(sender, instance, created, **kwargs):
    if created:
        ParticipantProfile.objects.create(user=instance)
```

- [ ] **Step 4: Add profile forms and views**

Create `NicknameForm` and `ParticipantProfileForm`; create `profile_prompt` that saves only `display_name`; create `profile_edit` for optional fields. Use `login_required` on both views.

- [ ] **Step 5: Add URLs**

In `apps/accounts/urls.py`:

```python
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("first-name/", views.profile_prompt, name="profile_prompt"),
    path("me/", views.profile_edit, name="profile_edit"),
]
```

- [ ] **Step 6: Add admin**

Register `ParticipantProfile` with list display: user, display name, batch, region, updated_at.

- [ ] **Step 7: Run migrations and tests**

Run: `python manage.py makemigrations accounts`

Run: `python manage.py migrate`

Run: `python manage.py test apps.accounts`

Expected: all account tests pass.

- [ ] **Step 8: Commit**

```bash
git add apps/accounts templates/registration templates/accounts
git commit -m "feat: add participant profiles"
```

## Task 3: Experiment Configuration Models and Admin

**Files:**
- Create: `apps/experiments/models.py`
- Create: `apps/experiments/defaults.py`
- Create: `apps/experiments/admin.py`
- Test: `apps/experiments/tests.py`

- [ ] **Step 1: Write model defaults test**

In `apps/experiments/tests.py`, assert a new batch defaults to 5-minute chat, moderate neutrality, highest-lowest strategy, and random round order.

- [ ] **Step 2: Create models**

Implement:

- `ExperimentBatch`
- `Topic`
- `TopicComment`
- `ScaleItem`
- `RatingScaleConfig`
- `AIMode`

Use explicit `TextField` pairs for Chinese and English participant-facing text, for example `title_zh`, `title_en`, `post_body_zh`, `post_body_en`.

- [ ] **Step 3: Add default prompt constants**

In `apps/experiments/defaults.py`, define `DEFAULT_AI_MODES` with the three Chinese prompt strings from the spec and matching English names/descriptions.

- [ ] **Step 4: Implement comment auto presentation**

Add fields on `TopicComment`:

```python
auto_author_name = models.CharField(max_length=80, blank=True)
avatar_seed = models.CharField(max_length=120, blank=True)
like_count = models.PositiveIntegerField(default=0)
relative_time = models.CharField(max_length=40, blank=True)
```

In `save()`, fill empty values deterministically using the comment primary data:

```python
seed_source = f"{self.topic_id}:{self.position}:{self.body_zh[:20]}"
```

Use a small fixed nickname pool and hash modulo selection.

- [ ] **Step 5: Configure Chinese admin**

Use inlines so a batch page can edit topics; a topic page can edit comments. Add list filters for batch and enabled status. Set model verbose names in Chinese.

- [ ] **Step 6: Run migrations and tests**

Run: `python manage.py makemigrations experiments`

Run: `python manage.py migrate`

Run: `python manage.py test apps.experiments`

Expected: experiment tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/experiments
git commit -m "feat: add experiment configuration models"
```

## Task 4: Survey State Machine and Snapshots

**Files:**
- Create: `apps/survey/models.py`
- Create: `apps/survey/services.py`
- Create: `apps/survey/admin.py`
- Test: `apps/survey/tests.py`

- [ ] **Step 1: Write state-machine tests**

Cover:

- Starting a session snapshots enabled topics in random order.
- Submitting topic order selects highest and lowest topics.
- Round order is randomized and saved.
- Accessing a completed step is rejected by service methods.

- [ ] **Step 2: Create survey models**

Implement:

- `SurveySession`
- `TopicRound`
- `ScaleResponse`
- `TextResponse`
- `ConversationMessage`
- `CommentReaction`
- `QualityEvent`

Store snapshots in `models.JSONField`:

```python
batch_snapshot = models.JSONField(default=dict)
topic_order_snapshot = models.JSONField(default=list)
material_snapshot = models.JSONField(default=dict)
step_started_at = models.JSONField(default=dict)
step_submitted_at = models.JSONField(default=dict)
```

- [ ] **Step 3: Define step constants**

In `apps/survey/services.py`:

```python
STEP_TOPIC_ORDER = "topic_order"
ROUND_STEPS = ["post", "emotion", "stance_before", "initial_text", "mode", "chat", "ai_eval", "stance_after", "final_text"]
SESSION_DONE = "done"
```

- [ ] **Step 4: Implement session service**

Implement:

- `get_or_create_session(user)`
- `submit_topic_order(session, ordered_topic_ids)`
- `current_step(session)`
- `start_current_step(session)`
- `complete_round_step(round_obj, step)`
- `advance_after_mode(round_obj, selected_mode_or_skip)`
- `record_quality_event(user, event_type, metadata)`

Raise `PermissionError` when a caller tries to submit a non-current or completed step.

- [ ] **Step 5: Run migrations and tests**

Run: `python manage.py makemigrations survey`

Run: `python manage.py migrate`

Run: `python manage.py test apps.survey`

Expected: state-machine tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/survey
git commit -m "feat: add survey state machine"
```

## Task 5: Participant Flow Views and Templates

**Files:**
- Create: `apps/survey/forms.py`
- Create: `apps/survey/views.py`
- Create: `apps/survey/urls.py`
- Create: templates under `templates/survey/`
- Modify: `templates/base.html`
- Test: `apps/survey/tests.py`

- [ ] **Step 1: Write view access tests**

Use Django test client to verify:

- Anonymous users redirect to login.
- Users without display name redirect to first-name page.
- Users with profile but no batch see a clear Chinese message.
- Completed step URLs redirect to the current step.

- [ ] **Step 2: Create base template**

`templates/base.html` includes:

- Chinese/English language switch form posting to `/i18n/setlang/`.
- Links to profile and logout.
- `static/survey/css/site.css`.
- CSRF token meta tag for JavaScript.

- [ ] **Step 3: Implement `survey:start` router**

`start` calls `get_or_create_session()` and redirects to the exact current step route.

- [ ] **Step 4: Implement step views**

Create one view per step:

- `topic_order`
- `post`
- `scale`
- `text_response`
- `mode_select`
- `chat`
- `done`

Each view checks state through `survey.services`, renders only current-step data, and posts through a matching form.

- [ ] **Step 5: Build templates**

Templates must display participant-facing content in the current request language. Use helper methods on snapshot dictionaries:

```django
{{ material.title }}
{{ material.post_body }}
{{ item.label }}
```

Prepare these localized values in the view context instead of branching deeply in templates.

- [ ] **Step 6: Run participant flow tests**

Run: `python manage.py test apps.survey`

Expected: flow tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/survey templates
git commit -m "feat: add participant survey flow"
```

## Task 6: Participant Frontend JavaScript and Styling

**Files:**
- Create: `static/survey/css/site.css`
- Create: `static/survey/js/quality-events.js`
- Create: `static/survey/js/topic-order.js`
- Create: `static/survey/js/rating.js`
- Create: `static/survey/js/recorder.js`
- Create: `static/survey/js/chat.js`
- Modify: survey templates to include scripts only where needed

- [ ] **Step 1: Add quality event endpoint test**

In `apps/survey/tests.py`, post JSON to the quality endpoint and assert a `QualityEvent` row is created.

- [ ] **Step 2: Implement quality event endpoint**

Add URL `survey/quality-event/`; accept event types `copy`, `paste`, `cut`, `contextmenu`, `refresh`, `shortcut`; reject other values with HTTP 400.

- [ ] **Step 3: Implement `quality-events.js`**

Register listeners for `copy`, `paste`, `cut`, `contextmenu`, and `keydown` combinations for Ctrl/Cmd+C/V/X. Prevent default and POST event JSON with CSRF token.

- [ ] **Step 4: Implement `topic-order.js`**

Support drag-and-drop plus up/down buttons. Maintain a hidden input named `ordered_topic_ids` containing comma-separated topic IDs.

- [ ] **Step 5: Implement `rating.js`**

Use button groups for scale values. Clicking a value updates a hidden input and visible active state.

- [ ] **Step 6: Implement responsive CSS**

Style:

- Social post card.
- Comment list with generated DiceBear avatar URLs.
- Large segmented ratings.
- Chat bubbles.
- Mobile-first layout with comfortable tap targets.

- [ ] **Step 7: Manual browser verification**

Run: `python manage.py runserver 127.0.0.1:8000`

Open `http://127.0.0.1:8000/survey/`.

Verify topic ordering, rating selection, comment reactions, and copy/paste blocking on desktop and a narrow viewport.

- [ ] **Step 8: Commit**

```bash
git add static templates apps/survey
git commit -m "feat: add participant interactions"
```

## Task 7: AI Chat and Speech-to-Text

**Files:**
- Create: `apps/ai/clients.py`
- Create: `apps/ai/prompts.py`
- Create: `apps/ai/views.py`
- Create: `apps/ai/urls.py`
- Test: `apps/ai/tests.py`
- Modify: `static/survey/js/recorder.js`
- Modify: `static/survey/js/chat.js`
- Modify: `templates/survey/step_chat.html`

- [ ] **Step 1: Write prompt composition tests**

Assert:

- Current UI language is included.
- Moderate neutrality text is added by default.
- Strict neutrality text is used when configured.
- Mode prompt is appended exactly once.

- [ ] **Step 2: Implement prompt builder**

`build_system_prompt(batch, mode, language)` returns a single system prompt containing global neutrality control, target response language, and admin mode prompt.

- [ ] **Step 3: Implement Dubrify client wrapper**

In `apps/ai/clients.py`, create:

- `chat_stream(messages, model)`
- `transcribe_audio(file_obj, model)`

Use `openai.OpenAI(api_key=settings.DUBRIFY_API_KEY, base_url=settings.DUBRIFY_BASE_URL)`.

- [ ] **Step 4: Add mockable service tests**

Use `unittest.mock` to verify chat view saves participant message, streams assistant chunks, then saves final assistant message.

- [ ] **Step 5: Implement chat endpoint**

POST `/ai/chat/<round_id>/` accepts text, checks the round is on `chat`, saves participant message, streams assistant response with `StreamingHttpResponse`, saves final assistant text, and returns stream chunks as text/event-stream.

- [ ] **Step 6: Implement transcription endpoint**

POST `/ai/transcribe/` accepts temporary audio upload, calls transcription client, deletes the temporary file object, returns JSON `{ "text": "...", "model": "..." }`. Do not create any persistent audio model.

- [ ] **Step 7: Implement recorder JavaScript**

Use `MediaRecorder` to capture audio, upload it, place returned text into the textarea or chat input, and mark hidden input `input_method=speech_to_text`.

- [ ] **Step 8: Implement chat JavaScript**

Lock the input while streaming. Append participant bubble immediately. Append assistant chunks into one assistant bubble. Re-enable input only after stream closes. Maintain 5-minute countdown and an “提前结束 / End early” button.

- [ ] **Step 9: Run AI tests**

Run: `python manage.py test apps.ai apps.survey`

Expected: prompt, transcription, and mocked streaming tests pass.

- [ ] **Step 10: Commit**

```bash
git add apps/ai static/survey/js templates/survey apps/survey
git commit -m "feat: add ai chat and transcription"
```

## Task 8: Admin Bulk User Creation

**Files:**
- Modify: `apps/accounts/admin.py`
- Create: `templates/admin/accounts/bulk_create_participants.html`
- Test: `apps/accounts/tests.py`

- [ ] **Step 1: Write bulk creation test**

Post usernames, initial password, and batch ID to the admin view; assert users are created, passwords are usable, and profiles are assigned to the batch.

- [ ] **Step 2: Add admin URL**

Override `ParticipantProfileAdmin.get_urls()` and add `bulk-create/`.

- [ ] **Step 3: Implement form**

Fields:

- `batch`
- `initial_password`
- `usernames`, one username per line

Validation rejects duplicate usernames in the pasted list and existing database usernames.

- [ ] **Step 4: Implement creation view**

Create each user with `User.objects.create_user(username=username, password=initial_password)`, then set `profile.batch = batch`.

- [ ] **Step 5: Run tests**

Run: `python manage.py test apps.accounts`

Expected: bulk creation tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts templates/admin
git commit -m "feat: add participant bulk creation"
```

## Task 9: Batch Exports

**Files:**
- Create: `apps/exports/services.py`
- Create: `apps/exports/views.py`
- Create: `apps/exports/urls.py`
- Create: `templates/admin/exports/batch_export.html`
- Test: `apps/exports/tests.py`
- Modify: `apps/experiments/admin.py`

- [ ] **Step 1: Write export service tests**

Create a batch with one participant, one session, one round, one scale response, one text response, one conversation message, and one quality event. Assert selected export sections appear in Excel sheet names and CSV zip filenames.

- [ ] **Step 2: Implement section builders**

In `apps/exports/services.py`, implement row builders:

- `participant_rows(batch)`
- `snapshot_rows(batch)`
- `topic_order_rows(batch)`
- `round_rows(batch)`
- `comment_reaction_rows(batch)`
- `scale_response_rows(batch)`
- `text_response_rows(batch)`
- `conversation_rows(batch)`
- `quality_event_rows(batch)`

Each row is a dict with stable English column keys and human-readable values.

- [ ] **Step 3: Implement Excel export**

Use openpyxl. One workbook, one worksheet per selected section. Header row uses the dict keys.

- [ ] **Step 4: Implement CSV zip export**

Use `zipfile.ZipFile` and `csv.DictWriter`. One CSV file per selected section.

- [ ] **Step 5: Implement admin export view**

Batch export page includes checkboxes for data sections and radio buttons for Excel or CSV. Response filename format:

```text
batch-<batch_id>-export-YYYYMMDD-HHMMSS.xlsx
batch-<batch_id>-export-YYYYMMDD-HHMMSS.zip
```

- [ ] **Step 6: Link export from batch admin**

Add a custom button or readonly link in `ExperimentBatchAdmin` pointing to the export page for that batch.

- [ ] **Step 7: Run export tests**

Run: `python manage.py test apps.exports`

Expected: Excel and CSV tests pass.

- [ ] **Step 8: Commit**

```bash
git add apps/exports apps/experiments/admin.py templates/admin
git commit -m "feat: add selectable batch exports"
```

## Task 10: Seed Data and Admin Defaults

**Files:**
- Create: `apps/experiments/management/commands/seed_defaults.py`
- Modify: `apps/experiments/defaults.py`
- Test: `apps/experiments/tests.py`

- [ ] **Step 1: Write seed command test**

Call `call_command("seed_defaults")`; assert one batch, 10 topics, default scale items, and three AI modes exist.

- [ ] **Step 2: Add default data**

Use neutral sample Chinese and English materials for local development. Mark the batch name as `示例批次 / Demo Batch`.

- [ ] **Step 3: Implement management command**

Create idempotent defaults using `get_or_create`. Running the command twice must not duplicate AI modes, scale items, or topics.

- [ ] **Step 4: Run seed tests**

Run: `python manage.py test apps.experiments`

Expected: seed command test passes.

- [ ] **Step 5: Commit**

```bash
git add apps/experiments
git commit -m "chore: add demo seed data"
```

## Task 11: End-to-End Verification

**Files:**
- Modify tests as needed for coverage
- Create: `README.md` updates

- [ ] **Step 1: Run full test suite**

Run: `python manage.py test`

Expected: all app tests pass.

- [ ] **Step 2: Run Django checks**

Run: `python manage.py check`

Expected: `System check identified no issues`.

- [ ] **Step 3: Manual happy path**

Run:

```bash
python manage.py migrate
python manage.py seed_defaults
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Manual verification:

- Admin can log in and see Chinese model labels.
- Admin can create a participant and assign the demo batch.
- Participant logs in, fills display name, ranks topics, completes one round with AI skip, completes one round with AI mode selection.
- Step backtracking redirects to current step.
- Copy/paste attempts are blocked and logged.
- Export page downloads Excel and CSV.

- [ ] **Step 4: Update README**

Document:

- Local install.
- Environment variables.
- Seed command.
- How to run tests.
- How to use admin bulk creation and export.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add local development guide"
```

## Spec Coverage Review

- Accounts and participant profile: Tasks 2 and 8.
- Batches, bilingual materials, topics, comments, scales, AI modes: Tasks 3 and 10.
- Fixed participant flow, highest/lowest topics, randomized round order: Tasks 4 and 5.
- Step locking and resume: Tasks 4 and 5.
- Social post and comment reactions: Tasks 5 and 6.
- Convenient rating controls: Task 6.
- AI mode ordering, skip behavior, streaming chat: Tasks 5 and 7.
- Speech-to-text without persistent audio: Task 7.
- Quality control logs: Tasks 4 and 6.
- Chinese admin and bulk account creation: Tasks 3 and 8.
- Selectable Excel and CSV exports: Task 9.
- Responsive participant UI and bilingual switching: Tasks 5 and 6.
- Production-oriented environment configuration: Tasks 1 and 11.

## Execution Notes

- Keep commits small and aligned to tasks.
- Do not commit `.env`, database files, temporary audio files, or generated exports.
- Use environment variables for Dubrify credentials during manual verification.
- If dependency installation or model API calls fail due to network restrictions, request sandbox escalation instead of working around the approval flow.
