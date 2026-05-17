# Chat Interrupt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "中断" button that aborts a streaming AI response mid-flight, saves the partial text to the database with an interrupted flag, and shows the flag in the admin AI conversation table.

**Architecture:** AbortController in the frontend kills the fetch; on AbortError the JS POSTs the partial content to a new `/ai/interrupt/<round_id>/` endpoint that writes a `ConversationMessage` with `was_interrupted=True`; the admin detail view renders a `pill-warn` badge on those rows.

**Tech Stack:** Django (sync view), Django ORM migration, Vanilla JS (AbortController + fetch)

---

## File Map

| File | Change |
|------|--------|
| `apps/survey/models.py` | Add `was_interrupted`, `interrupted_at` to `ConversationMessage` |
| `apps/survey/migrations/0005_conversationmessage_interrupted.py` | New migration |
| `apps/ai/views.py` | Add `interrupt_chat` sync view |
| `apps/ai/urls.py` | Register `interrupt/<int:round_id>/` |
| `apps/ai/tests.py` | Tests for interrupt endpoint |
| `static/survey/js/chat.js` | AbortController, button state, abort handler |
| `apps/experiments/admin_views.py` | Add `was_interrupted` to `conversation_rows` |
| `templates/admin/research/user_detail.html` | `pill-warn` CSS + badge in table |

---

### Task 1: Add model fields + migration

**Files:**
- Modify: `apps/survey/models.py`
- Create: `apps/survey/migrations/0005_conversationmessage_interrupted.py`

- [ ] **Step 1: Add fields to ConversationMessage**

In `apps/survey/models.py`, find the `ConversationMessage` class and add two fields after `error_message`:

```python
class ConversationMessage(models.Model):
    ROLES = [("participant", "参与者"), ("assistant", "AI"), ("system", "系统")]

    round = models.ForeignKey(TopicRound, on_delete=models.CASCADE, related_name="conversation_messages")
    role = models.CharField("角色", max_length=20, choices=ROLES)
    content = models.TextField("内容")
    language = models.CharField("语言", max_length=12)
    ai_mode_name = models.CharField("AI 模式", max_length=120, blank=True)
    model_name = models.CharField("模型名称", max_length=120, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    was_interrupted = models.BooleanField("被用户中断", default=False)
    interrupted_at = models.DateTimeField("中断时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
```

- [ ] **Step 2: Create migration**

Run:
```bash
python manage.py makemigrations survey --name conversationmessage_interrupted
```

Expected: Creates `apps/survey/migrations/0005_conversationmessage_interrupted.py`

- [ ] **Step 3: Apply migration**

Run:
```bash
python manage.py migrate
```

Expected: `OK` with no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/survey/models.py apps/survey/migrations/0005_conversationmessage_interrupted.py
git commit -m "feat: add was_interrupted and interrupted_at fields to ConversationMessage"
```

---

### Task 2: Backend interrupt endpoint + tests

**Files:**
- Modify: `apps/ai/tests.py`
- Modify: `apps/ai/views.py`
- Modify: `apps/ai/urls.py`

- [ ] **Step 1: Write failing tests**

Append the following class to `apps/ai/tests.py` (after the existing `AIViewTests` class):

```python
class InterruptChatTests(TransactionTestCase):
    def _round(self, username="interrupter"):
        user = User.objects.create_user(username, password="pass")
        batch = ExperimentBatch.objects.create(name=f"Batch {username}")
        mode = AIMode.objects.create(batch=batch, name_zh="总结", prompt_zh="请总结信息。")
        session = SurveySession.objects.create(user=user, batch=batch, language="zh-hans", topic_order_snapshot=[])
        round_obj = TopicRound.objects.create(
            session=session,
            round_type=TopicRound.HIGH,
            topic_id=1,
            current_step="chat",
            ai_mode=mode,
        )
        return user, round_obj

    def _provider(self, name="provider", model="model-a", key="key-a"):
        provider = LLMProvider.objects.create(
            name=name,
            model_name=model,
            base_url=f"https://{name}.example/v1",
            priority=1,
        )
        APIKey.objects.create(provider=provider, api_key=key, model_name="", is_active=True)
        return provider

    def test_interrupt_creates_message_with_partial_content(self):
        user, round_obj = self._round("i001")
        self._provider()
        self.client.force_login(user)

        response = self.client.post(
            reverse("ai:interrupt", args=[round_obj.pk]),
            {"partial_content": "这是被截断的"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        msg = ConversationMessage.objects.get(round=round_obj, role="assistant")
        self.assertEqual(msg.content, "这是被截断的")
        self.assertTrue(msg.was_interrupted)
        self.assertIsNotNone(msg.interrupted_at)
        self.assertEqual(msg.language, "zh-hans")
        self.assertEqual(msg.ai_mode_name, "总结")

    def test_interrupt_with_empty_content_is_allowed(self):
        user, round_obj = self._round("i002")
        self._provider()
        self.client.force_login(user)

        response = self.client.post(
            reverse("ai:interrupt", args=[round_obj.pk]),
            {"partial_content": ""},
        )

        self.assertEqual(response.status_code, 200)
        msg = ConversationMessage.objects.get(round=round_obj, role="assistant")
        self.assertEqual(msg.content, "")
        self.assertTrue(msg.was_interrupted)

    def test_interrupt_requires_login(self):
        _, round_obj = self._round("i003")

        response = self.client.post(
            reverse("ai:interrupt", args=[round_obj.pk]),
            {"partial_content": "some text"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConversationMessage.objects.filter(round=round_obj).exists())

    def test_interrupt_returns_404_for_wrong_user(self):
        _, round_obj = self._round("i004")
        other_user = User.objects.create_user("other_i004", password="pass")
        self.client.force_login(other_user)

        response = self.client.post(
            reverse("ai:interrupt", args=[round_obj.pk]),
            {"partial_content": "text"},
        )

        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python manage.py test apps.ai.tests.InterruptChatTests -v 2
```

Expected: All 4 tests fail with `NoReverseMatch` or `404` errors because the view and URL don't exist yet.

- [ ] **Step 3: Add the interrupt view to `apps/ai/views.py`**

Add these imports at the top of `apps/ai/views.py` if not already present (they already exist in the file except `timezone`):

```python
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
```

Then add the following function at the end of `apps/ai/views.py` (after the `transcribe` function):

```python
@login_required
@require_POST
def interrupt_chat(request, round_id):
    try:
        round_obj = TopicRound.objects.select_related(
            "session", "ai_mode"
        ).get(pk=round_id, session__user=request.user)
    except TopicRound.DoesNotExist:
        raise Http404

    partial_content = request.POST.get("partial_content", "")

    providers = configured_providers()
    model_name = ""
    if providers:
        key = providers[0].api_keys.filter(is_active=True).order_by("usage_count", "id").first()
        if key:
            model_name = key.default_model_name()
        else:
            model_name = providers[0].model_name

    ConversationMessage.objects.create(
        round=round_obj,
        role="assistant",
        content=partial_content,
        language=round_obj.session.language,
        ai_mode_name=round_obj.ai_mode.name_zh if round_obj.ai_mode else "",
        model_name=model_name,
        was_interrupted=True,
        interrupted_at=timezone.now(),
    )
    return JsonResponse({"ok": True})
```

- [ ] **Step 4: Register the URL in `apps/ai/urls.py`**

Replace the full contents of `apps/ai/urls.py`:

```python
from django.urls import path

from . import views


app_name = "ai"

urlpatterns = [
    path("chat/<int:round_id>/", views.chat, name="chat"),
    path("interrupt/<int:round_id>/", views.interrupt_chat, name="interrupt"),
    path("transcribe/", views.transcribe, name="transcribe"),
]
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python manage.py test apps.ai.tests.InterruptChatTests -v 2
```

Expected: All 4 tests PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
python manage.py test
```

Expected: All tests pass, no failures.

- [ ] **Step 7: Commit**

```bash
git add apps/ai/views.py apps/ai/urls.py apps/ai/tests.py
git commit -m "feat: add POST /ai/interrupt/<round_id>/ endpoint to save interrupted AI responses"
```

---

### Task 3: Frontend — AbortController + interrupt button

**Files:**
- Modify: `static/survey/js/chat.js`

- [ ] **Step 1: Replace the submit handler in `chat.js`**

The entire `form.addEventListener("submit", ...)` block (lines 224–270 in the current file) must be replaced with the following:

```js
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const input = form.querySelector("input[name=message]");
    const send = form.querySelector('button[type="submit"]');
    const text = input.value.trim();
    if (!text) return;
    bubble(text, "participant");
    input.value = "";
    input.disabled = true;
    if (send) send.disabled = true;
    const assistant = bubble("", "assistant", true);
    const revealer = createTextRevealer(assistant);
    setStatus("正在整理回复...", true);

    const controller = new AbortController();
    let firstChunk = true;

    function onAbortClick(e) {
      e.preventDefault();
      controller.abort();
    }

    const data = new FormData();
    data.append("message", text);
    try {
      const response = await fetch("/ai/chat/" + panel.dataset.roundId + "/", {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: data,
        signal: controller.signal,
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        blocks.forEach((block) => handleServerEvent(block, revealer, assistant));
        if (firstChunk) {
          firstChunk = false;
          if (send) {
            send.textContent = "中断";
            send.disabled = false;
            send.addEventListener("click", onAbortClick);
          }
        }
        setStatus("AI 正在回复...", true);
      }
      if (buffer) handleServerEvent(buffer, revealer, assistant);
      await revealer.finish();
    } catch (error) {
      if (error.name === "AbortError") {
        const partial = assistant.dataset.markdownSource || assistant.textContent || "";
        const tag = document.createElement("span");
        tag.className = "chat-interrupted-tag";
        tag.textContent = " 「已中断」";
        assistant.appendChild(tag);
        const interruptData = new FormData();
        interruptData.append("partial_content", partial);
        fetch("/ai/interrupt/" + panel.dataset.roundId + "/", {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken() },
          body: interruptData,
        }).catch(function () {});
      } else {
        assistant.classList.add("error");
        revealer.push("暂时没有收到稳定回复，请稍后再试一次。");
        await revealer.finish();
      }
    } finally {
      setStatus("", false);
      if (send) {
        send.textContent = "发送";
        send.disabled = false;
        send.removeEventListener("click", onAbortClick);
      }
      input.disabled = false;
      input.focus();
    }
  });
```

- [ ] **Step 2: Manual smoke test**

Start the dev server:
```bash
python manage.py runserver
```

Log in as a participant, navigate to a chat round, send a message, and immediately click "中断" while the AI is streaming. Verify:
- Button changes from "发送" → "中断" when AI starts responding
- Clicking "中断" stops the stream
- Bubble shows partial text + ` 「已中断」` appended
- Button reverts to "发送", input re-enabled
- A new message can be sent normally afterward

- [ ] **Step 3: Commit**

```bash
git add static/survey/js/chat.js
git commit -m "feat: add interrupt button to chat UI with AbortController"
```

---

### Task 4: Admin display — interrupted badge

**Files:**
- Modify: `apps/experiments/admin_views.py`
- Modify: `templates/admin/research/user_detail.html`

- [ ] **Step 1: Add `was_interrupted` to conversation_rows in `admin_views.py`**

In `apps/experiments/admin_views.py`, find the `conversation_rows` list comprehension inside `user_detail` (around line 364). Replace it:

```python
    conversation_rows = [
        {
            "round_label": _round_label(item.round),
            "topic_title": _round_topic_title(item.round, topic_titles),
            "role": ROLE_LABELS.get(item.role, item.get_role_display()),
            "content": item.content,
            "model_name": item.model_name,
            "error_message": item.error_message,
            "was_interrupted": item.was_interrupted,
            "created_at": item.created_at,
        }
        for item in conversation_messages
    ]
```

- [ ] **Step 2: Add `pill-warn` CSS to `user_detail.html`**

In `templates/admin/research/user_detail.html`, find the `.pill` CSS rule (around line 143) and add `.pill-warn` immediately after:

```css
  .pill {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    border-radius: 999px;
    padding: 5px 10px;
    background: #edf7ff;
    color: #0077bf;
    font-weight: 800;
    font-size: 13px;
  }

  .pill-warn {
    background: #fff8e1;
    color: #b45309;
  }
```

- [ ] **Step 3: Add interrupted badge to the AI conversation table**

In `templates/admin/research/user_detail.html`, find the "模型 / 状态" cell (around line 361):

```html
                <td>
                  {{ item.model_name|default:"-" }}
                  {% if item.error_message %}<br><span class="muted">调用失败：{{ item.error_message|truncatechars:80 }}</span>{% endif %}
                </td>
```

Replace with:

```html
                <td>
                  {{ item.model_name|default:"-" }}
                  {% if item.was_interrupted %}<br><span class="pill pill-warn">已中断</span>{% endif %}
                  {% if item.error_message %}<br><span class="muted">调用失败：{{ item.error_message|truncatechars:80 }}</span>{% endif %}
                </td>
```

- [ ] **Step 4: Manual smoke test of admin display**

Log in as staff, go to the research admin user detail page for a participant who triggered an interrupt. Verify:
- The interrupted AI message row shows the partial content
- The "模型 / 状态" column shows a yellow "已中断" badge
- Non-interrupted rows are unaffected

- [ ] **Step 5: Run full test suite**

```bash
python manage.py test
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/experiments/admin_views.py templates/admin/research/user_detail.html
git commit -m "feat: show interrupted AI messages with badge in admin conversation table"
```
