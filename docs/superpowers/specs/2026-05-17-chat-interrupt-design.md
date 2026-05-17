# Chat Interrupt Feature Design

**Date:** 2026-05-17  
**Status:** Approved

## Overview

Add an interrupt button to the chat interface. While the AI is streaming a response, the "发送" button transforms into a "中断" button. Clicking it aborts the stream, saves the partial response to the database with an interrupted flag, and restores the UI. Admin can see the truncated message clearly marked in the AI conversation table.

## Data Model

Add two fields to `ConversationMessage` (`apps/survey/models.py`):

```python
was_interrupted = models.BooleanField("被用户中断", default=False)
interrupted_at = models.DateTimeField("中断时间", null=True, blank=True)
```

The `content` field stores whatever partial text was received at the moment of interruption (may be an empty string). A new migration is required.

## Backend

### New endpoint

`POST /ai/interrupt/<round_id>/`  
Registered in `apps/ai/urls.py`.

**Request body (form data):**
- `partial_content` — the AI text fragment already received by the frontend

**Logic (`apps/ai/views.py`):**
1. Authenticate user, look up `TopicRound` by `round_id` owned by that user.
2. Always create a new `ConversationMessage` (the streaming endpoint only writes the assistant record after the full stream completes, so no in-progress record exists at interrupt time).
3. Write `partial_content` → `content`, `role="assistant"`, `was_interrupted=True`, `interrupted_at=now()`, plus `language`, `ai_mode_name`, `model_name` copied from round context.
4. Return `JsonResponse({"ok": True})`.

## Frontend (`static/survey/js/chat.js`)

Changes inside the `submit` event handler:

1. Create `AbortController` before `fetch`; pass `signal` to fetch options.
2. Once the first SSE chunk arrives, change send button `textContent` to `"中断"` and wire a one-time `click` listener that calls `controller.abort()`.
3. In the `catch` block, check `error.name === "AbortError"`:
   - Collect the text already rendered by `revealer` (from `assistant.dataset.markdownSource || assistant.textContent`).
   - Append `「已中断」` to the bubble content.
   - POST to `/ai/interrupt/<round_id>/` with `partial_content`.
4. In `finally`, restore button text to `"发送"`, re-enable input and button, remove the abort click listener.

Non-abort errors follow the existing error path unchanged.

## Admin Display (`admin_views.py` + `user_detail.html`)

In `user_detail` view, `conversation_rows` gains:

```python
"was_interrupted": item.was_interrupted,
```

In `user_detail.html` AI conversation table, "模型 / 状态" column:

```html
{% if item.was_interrupted %}
  <br><span class="pill pill-warn">已中断</span>
{% endif %}
```

The `pill-warn` class does not exist yet and must be added as inline CSS in `user_detail.html`:

```css
.pill-warn {
  background: #fff8e1;
  color: #b45309;
}
```

## Scope

- No changes to the streaming endpoint `/ai/chat/<round_id>/`.
- No changes to the countdown timer or finish-round logic.
- No changes to `QualityEvent`.
- One new migration file required.
