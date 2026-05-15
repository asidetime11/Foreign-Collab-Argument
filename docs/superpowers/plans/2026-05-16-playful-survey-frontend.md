# 轻松小游戏化问卷前端实现计划

> **给执行代理：** 必须使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务逐项实现。本计划使用复选框语法跟踪进度。

**目标：** 按已确认设计，把参与者端答题流程改造成中文、轻松、有任务感但不花哨的小游戏化界面。

**架构：** 后端流程和数据模型尽量保持不变，重点改造模板、样式和前端脚本。少量视图上下文用于提供统一站点进度、标题和步骤说明；所有用户可见交互保持中文。

**技术栈：** Django 模板、Django 测试、原生 CSS、原生 JavaScript、现有质量事件接口。

---

## 文件结构

- 修改 `apps/survey/views.py`：给各步骤模板传入统一的站点进度、步骤标题、提示文案；把参与者端语言固定为中文；模式选择保持前三项随机、“跳过”最后。
- 修改 `apps/survey/forms.py`：开放回答必须有内容，量表字段保留必答，表单错误保持中文。
- 修改 `apps/survey/tests.py`：覆盖每个关键交互规则和中文文案。
- 修改 `templates/base.html`：保留全局页头，但改成轻量任务风格所需结构。
- 修改 `templates/survey/*.html`：重写参与者端每一步模板结构。
- 修改 `static/survey/css/site.css`：实现克制的软糖任务板风格，统一优化背景、按钮、输入框、任务卡、路线进度和移动端适配。
- 修改 `static/survey/js/topic-order.js`：维护排名、拖拽排序、上移下移、提交同步。
- 修改 `static/survey/js/rating.js`：支持点击刻度和拖动滑条，默认未选择，完成后显示状态。
- 修改 `static/survey/js/quality-events.js`：阻止作答输入中的复制粘贴、拖入文本、右键粘贴，并记录事件。
- 修改 `static/survey/js/chat.js`：中文聊天界面提示、禁止粘贴配合、倒计时和结束按钮文案。

## 任务 1：补充统一步骤上下文和回归测试

**文件：**

- 修改：`apps/survey/views.py`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中给 `SurveyViewTests` 增加以下测试，验证中文站点标题、进度文本、第一步提交按钮和排序规则提示。

```python
    def test_topic_order_page_has_playful_chinese_step_context(self):
        user = User.objects.create_user("p_topic", password="pass")
        batch = ExperimentBatch.objects.create(
            name="批次 A",
            intro_zh="请按照你的真实想法排序。",
            is_active=True,
        )
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        for index in range(10):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))

        self.assertContains(response, "第 1 站 / 共 11 站")
        self.assertContains(response, "先排一排你最在意的话题")
        self.assertContains(response, "从上到下：最重要 → 最不重要")
        self.assertContains(response, "确认排序")
        self.assertContains(response, "提交后将进入下一站，排序不能返回修改。")
        self.assertNotContains(response, "提交排序")
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_topic_order_page_has_playful_chinese_step_context
```

预期：失败，页面还没有新的站点进度、标题和按钮文案。

- [ ] **步骤 3：实现统一步骤上下文**

在 `apps/survey/views.py` 中增加常量和辅助函数：

```python
STEP_META = {
    "topic_order": {"number": 1, "title": "先排一排你最在意的话题", "kind": "sort"},
    "post": {"number": 2, "title": "阅读帖子与评论", "kind": "read"},
    "emotion": {"number": 3, "title": "当前感受", "kind": "mood"},
    "stance_before": {"number": 4, "title": "你的观点", "kind": "stance"},
    "initial_text": {"number": 5, "title": "写下你的想法", "kind": "text"},
    "mode": {"number": 6, "title": "选择对话模式", "kind": "mode"},
    "chat": {"number": 7, "title": "与人工智能对话", "kind": "chat"},
    "ai_eval": {"number": 8, "title": "对人工智能的评价", "kind": "ai_eval"},
    "stance_after": {"number": 9, "title": "再次确认你的观点", "kind": "stance"},
    "final_text": {"number": 10, "title": "写下你的新想法", "kind": "text"},
    "done": {"number": 11, "title": "已完成，感谢你的参与", "kind": "done"},
}


def _step_context(step):
    meta = STEP_META[step].copy()
    meta["total"] = 11
    meta["label"] = f"第 {meta['number']} 站 / 共 11 站"
    meta["route"] = range(1, 12)
    return meta
```

在各个 `render` 调用中加入 `step_meta`，第一步示例：

```python
return render(
    request,
    "survey/step_topic_order.html",
    {"form": form, "session": session, "topics": topics, "step_meta": _step_context("topic_order")},
)
```

- [ ] **步骤 4：临时更新第一步模板让测试通过**

在 `templates/survey/step_topic_order.html` 中先替换标题、提示和按钮文案：

```django
<p class="step-label">{{ step_meta.label }}</p>
<h1>{{ step_meta.title }}</h1>
<p class="sort-rule">从上到下：最重要 → 最不重要</p>
...
<p class="submit-note">提交后将进入下一站，排序不能返回修改。</p>
<button class="primary" type="submit">确认排序</button>
```

- [ ] **步骤 5：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_topic_order_page_has_playful_chinese_step_context
```

预期：通过。

## 任务 2：实现克制的全局软糖任务板骨架

**文件：**

- 修改：`templates/base.html`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证参与者页面不出现语言切换入口，并出现中文品牌。

```python
    def test_participant_pages_use_chinese_task_shell(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "观点小任务")
        self.assertNotContains(response, "English")
        self.assertNotContains(response, 'name="language"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_participant_pages_use_chinese_task_shell
```

预期：失败，因为品牌仍是旧文案或结构未完全改造。

- [ ] **步骤 3：改造基础模板**

将 `templates/base.html` 的页头品牌改成中文任务风格，并保留登录状态操作：

```django
<header class="topbar">
  <a class="brand" href="{% url 'survey:start' %}">观点小任务</a>
  <nav class="top-actions">
    {% if user.is_authenticated %}
      <a href="{% url 'accounts:profile_edit' %}">资料</a>
      <form action="{% url 'logout' %}" method="post" class="inline">{% csrf_token %}<button type="submit">退出</button></form>
    {% endif %}
  </nav>
</header>
```

- [ ] **步骤 4：替换全局样式基础变量**

在 `static/survey/css/site.css` 顶部设置中文字体、克制明亮背景、8 像素圆角、路线色彩：

```css
:root {
  color-scheme: light;
  --ink: #26303d;
  --muted: #6f7885;
  --line: #27313f;
  --paper: #fffaf0;
  --blue: #55b6ff;
  --green: #68d99a;
  --yellow: #ffd166;
  --pink: #ff8cb4;
  --panel: rgba(255, 255, 255, .9);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  background: #fffdf7;
  color: var(--ink);
}
```

添加全局背景、页头、主容器、任务面板、路线点样式，保持 `.panel`、`.post-card`、`.primary` 这些现有类名可用。背景只使用柔和底色、轻微光感和页面层次，不加入大面积装饰图案。

- [ ] **步骤 5：统一优化按钮和表单基础控件**

在 `static/survey/css/site.css` 中统一按钮、输入框、文本框和禁用态。主要按钮要清楚但不夸张，次要按钮要轻，所有控件保持中文任务工具气质：

```css
button,
.primary,
input,
textarea,
select {
  font: inherit;
}

button,
.button {
  border: 2px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  padding: 10px 14px;
  cursor: pointer;
  transition: transform .12s ease, background-color .12s ease, box-shadow .12s ease;
}

button:hover {
  background: #fff7d6;
}

button:active {
  transform: translateY(1px);
}

button:disabled {
  cursor: not-allowed;
  opacity: .55;
}

.primary {
  background: var(--green);
  border-color: var(--line);
  color: var(--ink);
  font-weight: 800;
  box-shadow: 3px 3px 0 rgba(39, 49, 63, .72);
}

input,
textarea,
select {
  width: 100%;
  border: 2px solid rgba(39, 49, 63, .26);
  border-radius: 8px;
  background: rgba(255, 255, 255, .92);
  color: var(--ink);
  padding: 11px 12px;
}

input:focus,
textarea:focus,
select:focus {
  outline: 3px solid rgba(85, 182, 255, .28);
  border-color: var(--blue);
}
```

- [ ] **步骤 6：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_participant_pages_use_chinese_task_shell
```

预期：通过。

## 任务 3：重做第 1 站话题排序

**文件：**

- 修改：`templates/survey/step_topic_order.html`
- 修改：`static/survey/js/topic-order.js`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证 10 个话题卡片、排名、上下移动按钮和隐藏排序值都存在。

```python
    def test_topic_order_page_renders_ranked_cards_and_controls(self):
        user = User.objects.create_user("p_sort", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", intro_zh="排序说明", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        for index in range(10):
            Topic.objects.create(batch=batch, title_zh=f"话题 {index + 1}", position=index)
        self.client.force_login(user)

        response = self.client.get(reverse("survey:topic_order"))

        self.assertContains(response, 'class="topic-card"', count=10)
        self.assertContains(response, "第 1 位")
        self.assertContains(response, "第 10 位")
        self.assertContains(response, 'data-move="up"')
        self.assertContains(response, 'data-move="down"')
        self.assertContains(response, 'name="ordered_topic_ids"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_topic_order_page_renders_ranked_cards_and_controls
```

预期：失败，因为模板仍使用旧 `li` 结构。

- [ ] **步骤 3：重写第一步模板**

将 `templates/survey/step_topic_order.html` 主体改成任务页结构：

```django
<section class="task-page task-page-sort">
  {% include "survey/partials/step_header.html" %}
  <div class="task-hero">
    <div>
      <p class="step-label">{{ step_meta.label }}</p>
      <h1>{{ step_meta.title }}</h1>
      <p class="intro-text">{{ session.batch_snapshot.intro_zh }}</p>
    </div>
    <aside class="mission-card">
      <strong data-sort-count>排序已完成 {{ topics|length }} / {{ topics|length }}</strong>
      <span>从上到下：最重要 → 最不重要</span>
    </aside>
  </div>
  <form method="post" class="task-form">
    {% csrf_token %}
    {{ form.ordered_topic_ids }}
    <ol id="topic-list" class="topic-list" aria-label="话题排序">
      {% for topic in topics %}
        <li class="topic-card" draggable="true" data-topic-id="{{ topic.id }}">
          <span class="topic-rank">第 {{ forloop.counter }} 位</span>
          <span class="topic-title">{{ topic.title }}</span>
          <span class="topic-actions">
            <button type="button" data-move="up" aria-label="上移 {{ topic.title }}">↑</button>
            <button type="button" data-move="down" aria-label="下移 {{ topic.title }}">↓</button>
          </span>
        </li>
      {% endfor %}
    </ol>
    <div class="sticky-submit">
      <strong>提交后将进入下一站，排序不能返回修改。</strong>
      <button class="primary" type="submit">确认排序</button>
    </div>
  </form>
</section>
```

- [ ] **步骤 4：新增步骤头部局部模板**

创建 `templates/survey/partials/step_header.html`：

```django
<div class="step-route" aria-label="答题进度">
  {% for number in step_meta.route %}
    <span class="route-dot{% if number == step_meta.number %} active{% elif number < step_meta.number %} done{% endif %}"></span>
  {% endfor %}
</div>
```

- [ ] **步骤 5：更新排序脚本**

修改 `static/survey/js/topic-order.js`，同步隐藏值和排名：

```javascript
(function () {
  const list = document.getElementById("topic-list");
  const input = document.querySelector('input[name="ordered_topic_ids"]');
  if (!list || !input) return;

  function items() {
    return Array.from(list.querySelectorAll("[data-topic-id]"));
  }

  function sync() {
    input.value = items().map((item) => item.dataset.topicId).join(",");
    items().forEach((item, index) => {
      const rank = item.querySelector(".topic-rank");
      if (rank) rank.textContent = `第 ${index + 1} 位`;
      item.classList.toggle("is-first", index === 0);
      item.classList.toggle("is-last", index === items().length - 1);
    });
  }

  let dragged = null;
  list.addEventListener("dragstart", (event) => {
    dragged = event.target.closest("[data-topic-id]");
    if (dragged) dragged.classList.add("dragging");
  });
  list.addEventListener("dragend", () => {
    if (dragged) dragged.classList.remove("dragging");
    dragged = null;
    sync();
  });
  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest("[data-topic-id]");
    if (!target || !dragged || target === dragged) return;
    const rect = target.getBoundingClientRect();
    list.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? target : target.nextSibling);
    sync();
  });
  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-move]");
    if (!button) return;
    const item = button.closest("[data-topic-id]");
    if (button.dataset.move === "up" && item.previousElementSibling) {
      list.insertBefore(item, item.previousElementSibling);
    }
    if (button.dataset.move === "down" && item.nextElementSibling) {
      list.insertBefore(item.nextElementSibling, item);
    }
    sync();
  });
  sync();
})();
```

- [ ] **步骤 6：添加排序页面样式**

在 `static/survey/css/site.css` 中添加 `.task-page`、`.task-hero`、`.mission-card`、`.topic-list`、`.topic-card`、`.sticky-submit` 和移动端规则。

- [ ] **步骤 7：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_topic_order_page_renders_ranked_cards_and_controls
```

预期：通过。

## 任务 4：重做第 2 站评论赞踩

**文件：**

- 修改：`templates/survey/step_post.html`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证评论使用按钮式单选项，并保留“不选择”状态。

```python
    def test_post_page_renders_optional_like_dislike_controls(self):
        user = User.objects.create_user("p_post", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        round_obj = session.rounds.create(
            round_type="high",
            topic_id=1,
            current_step="post",
            material_snapshot={
                "title_zh": "话题",
                "post_body_zh": "帖子正文",
                "comments": [{"id": 1, "author": "参与者 A", "avatar_seed": "a", "relative_time": "刚刚", "like_count": 2, "body_zh": "评论正文"}],
            },
        )
        self.client.force_login(user)

        response = self.client.get(reverse("survey:post"))

        self.assertContains(response, "阅读帖子与评论")
        self.assertContains(response, "赞")
        self.assertContains(response, "踩")
        self.assertContains(response, 'value="none"')
        self.assertContains(response, 'class="reaction-choice"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_post_page_renders_optional_like_dislike_controls
```

预期：失败，因为模板还是普通单选标签。

- [ ] **步骤 3：重写评论模板**

将评论区改成留言条和按钮式单选：

```django
<article class="comment-card">
  <img alt="" src="https://api.dicebear.com/8.x/thumbs/svg?seed={{ comment.avatar_seed }}">
  <div class="comment-body">
    <div class="comment-meta"><strong>{{ comment.author }}</strong><span>{{ comment.relative_time }} · {{ comment.like_count }} 赞</span></div>
    <p>{{ comment.body }}</p>
    <div class="reaction-group">
      <label class="reaction-choice"><input type="radio" name="comment_{{ comment.id }}" value="none" checked>不选择</label>
      <label class="reaction-choice"><input type="radio" name="comment_{{ comment.id }}" value="like">赞</label>
      <label class="reaction-choice"><input type="radio" name="comment_{{ comment.id }}" value="dislike">踩</label>
    </div>
  </div>
</article>
```

- [ ] **步骤 4：添加评论样式**

在 `site.css` 中给 `.comment-card`、`.reaction-group`、`.reaction-choice` 添加轻松留言条样式，并用 `:has(input:checked)` 显示选中态。

- [ ] **步骤 5：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_post_page_renders_optional_like_dislike_controls
```

预期：通过。

## 任务 5：重做量表交互

**文件：**

- 修改：`templates/survey/step_scale.html`
- 修改：`static/survey/js/rating.js`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 增加测试，验证情绪页为心情调音台，默认隐藏值为空，包含点击刻度和滑条。

```python
    def test_scale_page_renders_clickable_slider_controls(self):
        user = User.objects.create_user("p_scale", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        session.rounds.create(round_type="high", topic_id=1, current_step="stance_before", material_snapshot={"statement_zh": "观点"})
        self.client.force_login(user)

        response = self.client.get(reverse("survey:scale", args=["stance_before"]))

        self.assertContains(response, "你的观点")
        self.assertContains(response, 'class="rating-track"')
        self.assertContains(response, 'data-value="1"')
        self.assertContains(response, 'data-value="7"')
        self.assertContains(response, 'type="hidden"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_scale_page_renders_clickable_slider_controls
```

预期：失败，因为没有 `.rating-track`。

- [ ] **步骤 3：重写量表模板**

使用根据 `step` 切换的标题和说明：

```django
<section class="task-page task-page-scale task-{{ step }}">
  {% include "survey/partials/step_header.html" %}
  <div class="task-hero compact">
    <p class="step-label">{{ step_meta.label }}</p>
    <h1>{{ step_meta.title }}</h1>
    {% if step == "stance_after" %}<p class="intro-text">前面的回答已收起，请根据现在的想法重新选择。</p>{% endif %}
  </div>
  <form method="post" class="task-form rating-form">
    {% csrf_token %}
    {% for item in items %}
      <fieldset class="rating-card" data-min="{{ item.min_value }}" data-max="{{ item.max_value }}">
        <legend>{{ item.label_zh }}</legend>
        <input type="hidden" name="item_{{ item.pk }}" required>
        <div class="rating-track" role="group" aria-label="{{ item.label_zh }}">
          {% for value in "1234567" %}
            <button type="button" data-value="{{ value }}"><span>{{ value }}</span></button>
          {% endfor %}
        </div>
      </fieldset>
    {% endfor %}
    <div class="sticky-submit"><strong>每一项都选择后才能继续。</strong><button class="primary" type="submit">继续</button></div>
  </form>
</section>
```

- [ ] **步骤 4：更新评分脚本**

修改 `rating.js` 支持按钮点击、拖动和必答状态：

```javascript
(function () {
  document.querySelectorAll(".rating-card").forEach((field) => {
    const input = field.querySelector("input[type=hidden]");
    const buttons = Array.from(field.querySelectorAll("[data-value]"));

    function select(button) {
      input.value = button.dataset.value;
      buttons.forEach((node) => node.classList.toggle("active", node === button));
      field.classList.add("answered");
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => select(button));
      button.addEventListener("pointerenter", (event) => {
        if (event.buttons === 1) select(button);
      });
    });
  });
})();
```

- [ ] **步骤 5：添加量表样式**

在 `site.css` 中添加 `.rating-card`、`.rating-track`、`.rating-track button.active`，情绪页用多色调音台风格，观点和人工智能评价页使用更聚焦的大号判断条。

- [ ] **步骤 6：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_scale_page_renders_clickable_slider_controls
```

预期：通过。

## 任务 6：重做开放回答和禁止复制粘贴

**文件：**

- 修改：`templates/survey/step_text.html`
- 修改：`static/survey/js/quality-events.js`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证想法便签、保存按钮和禁止粘贴标记。

```python
    def test_text_response_page_renders_note_and_no_paste_marker(self):
        user = User.objects.create_user("p_text", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        session.rounds.create(round_type="high", topic_id=1, current_step="initial_text", material_snapshot={})
        self.client.force_login(user)

        response = self.client.get(reverse("survey:text_response", args=["initial_text"]))

        self.assertContains(response, "写下你的想法")
        self.assertContains(response, "把你现在想到的写下来就好")
        self.assertContains(response, "保存想法")
        self.assertContains(response, 'data-no-paste="true"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_text_response_page_renders_note_and_no_paste_marker
```

预期：失败，因为模板还没有便签和 `data-no-paste`。

- [ ] **步骤 3：重写文本模板**

将 `step_text.html` 改成便签样式，并区分第 5 站和第 10 站提示：

```django
<section class="task-page task-page-text">
  {% include "survey/partials/step_header.html" %}
  <div class="task-hero compact">
    <p class="step-label">{{ step_meta.label }}</p>
    <h1>{{ step_meta.title }}</h1>
    {% if step == "final_text" %}
      <p class="intro-text">请再次写下你现在的想法，可以和之前相同，也可以不同。</p>
    {% else %}
      <p class="intro-text">把你现在想到的写下来就好，不需要标准答案。</p>
    {% endif %}
  </div>
  <form method="post" class="task-form note-form">
    {% csrf_token %}
    <div class="thought-note">
      <textarea name="final_text" required data-no-paste="true" placeholder="请直接输入你的想法，不要复制粘贴。">{{ form.final_text.value|default_if_none:"" }}</textarea>
    </div>
    {{ form.input_method }}
    {{ form.transcribe_model }}
    <label class="check-row">{{ form.was_edited }} 我编辑过转写文本</label>
    <div class="text-actions">
      <button type="button" data-recorder>语音输入</button>
      <button class="primary" type="submit">保存想法</button>
    </div>
  </form>
</section>
```

- [ ] **步骤 4：更新禁止粘贴脚本**

修改 `quality-events.js`，对 `[data-no-paste="true"]` 拦截 `paste`、`drop`、`contextmenu`，显示中文提示并调用现有质量事件接口：

```javascript
(function () {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";

  function record(eventType, metadata) {
    fetch("/survey/quality-event/", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": token},
      body: JSON.stringify({event_type: eventType, metadata}),
      keepalive: true,
    }).catch(() => {});
  }

  function showWarning(target) {
    const form = target.closest("form") || document.body;
    let warning = form.querySelector("[data-no-paste-warning]");
    if (!warning) {
      warning = document.createElement("p");
      warning.dataset.noPasteWarning = "true";
      warning.className = "form-warning";
      warning.textContent = "请直接输入你的想法，不要复制粘贴。";
      form.prepend(warning);
    }
  }

  document.addEventListener("paste", (event) => {
    const target = event.target.closest?.('[data-no-paste="true"]');
    if (!target) return;
    event.preventDefault();
    showWarning(target);
    record("paste", {path: window.location.pathname});
  });

  document.addEventListener("drop", (event) => {
    const target = event.target.closest?.('[data-no-paste="true"]');
    if (!target) return;
    event.preventDefault();
    showWarning(target);
    record("paste", {path: window.location.pathname, source: "drop"});
  });

  document.addEventListener("contextmenu", (event) => {
    const target = event.target.closest?.('[data-no-paste="true"]');
    if (!target) return;
    event.preventDefault();
    showWarning(target);
    record("contextmenu", {path: window.location.pathname});
  });
})();
```

- [ ] **步骤 5：添加便签样式**

在 `site.css` 中添加 `.thought-note textarea`、`.text-actions`、`.form-warning` 和移动端布局。

- [ ] **步骤 6：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_text_response_page_renders_note_and_no_paste_marker
```

预期：通过。

## 任务 7：重做第 6 站模式选择

**文件：**

- 修改：`templates/survey/step_mode.html`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证“跳过”按钮最后出现且有任务卡类名。

```python
    def test_mode_page_renders_mode_cards_with_skip_last(self):
        user = User.objects.create_user("p_mode", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        session.rounds.create(round_type="high", topic_id=1, current_step="mode", material_snapshot={})
        self.client.force_login(user)

        response = self.client.get(reverse("survey:mode_select"))
        content = response.content.decode()

        self.assertContains(response, "选择对话模式")
        self.assertContains(response, 'class="mode-card"')
        self.assertLess(content.rfind('value="skip"'), content.rfind("</form>"))
        self.assertContains(response, "跳过")
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_mode_page_renders_mode_cards_with_skip_last
```

预期：失败，因为没有模式卡样式。

- [ ] **步骤 3：重写模式模板**

将 `step_mode.html` 改成卡片网格：

```django
<section class="task-page task-page-mode">
  {% include "survey/partials/step_header.html" %}
  <div class="task-hero compact">
    <p class="step-label">{{ step_meta.label }}</p>
    <h1>{{ step_meta.title }}</h1>
    <p class="intro-text">接下来可以选择一种方式和人工智能聊一聊，也可以跳过。</p>
  </div>
  <form method="post" class="mode-grid">
    {% csrf_token %}
    {% for mode in modes %}
      <button class="mode-card" name="selected_mode" value="{{ mode.pk }}" type="submit">
        <strong>{{ mode.name_zh }}</strong>
        <span>{{ mode.prompt_zh|truncatechars:42 }}</span>
      </button>
    {% endfor %}
    <button class="mode-card skip-card" name="selected_mode" value="skip" type="submit">
      <strong>跳过</strong>
      <span>不使用人工智能，直接进入下一站。</span>
    </button>
  </form>
</section>
```

- [ ] **步骤 4：添加模式卡样式**

在 `site.css` 中添加 `.mode-grid`、`.mode-card`、`.skip-card`，让前三张卡片轻松明亮，跳过卡片视觉较低调但仍清楚。

- [ ] **步骤 5：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_mode_page_renders_mode_cards_with_skip_last
```

预期：通过。

## 任务 8：重做第 7 站聊天页

**文件：**

- 修改：`templates/survey/step_chat.html`
- 修改：`static/survey/js/chat.js`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证聊天页中文文案、倒计时、结束按钮和禁止粘贴。

```python
    def test_chat_page_renders_chinese_game_chat_ui(self):
        user = User.objects.create_user("p_chat", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True, ai_chat_minutes=5)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        session = SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_ROUND,
            batch_snapshot={},
            topic_order_snapshot=[],
        )
        session.rounds.create(round_type="high", topic_id=1, current_step="chat", material_snapshot={})
        self.client.force_login(user)

        response = self.client.get(reverse("survey:chat"))

        self.assertContains(response, "与人工智能对话")
        self.assertContains(response, "剩余时间")
        self.assertContains(response, "完成这轮对话")
        self.assertContains(response, 'data-no-paste="true"')
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_chat_page_renders_chinese_game_chat_ui
```

预期：失败，因为旧模板没有这些文案。

- [ ] **步骤 3：重写聊天模板**

将 `step_chat.html` 改成聊天任务页：

```django
<section class="task-page task-page-chat chat" data-round-id="{{ round.pk }}" data-minutes="{{ minutes }}">
  {% include "survey/partials/step_header.html" %}
  <div class="chat-head">
    <div>
      <p class="step-label">{{ step_meta.label }}</p>
      <h1>{{ step_meta.title }}</h1>
    </div>
    <div class="timer">剩余时间 <strong data-countdown>{{ minutes }}:00</strong></div>
  </div>
  <div id="chat-log" class="chat-log" aria-live="polite"></div>
  <form id="chat-form" class="chat-input-row">
    {% csrf_token %}
    <input name="message" autocomplete="off" data-no-paste="true" placeholder="直接输入你想聊的内容">
    <button type="submit">发送</button>
  </form>
  <form method="post" class="chat-finish">{% csrf_token %}<button class="primary" type="submit">完成这轮对话</button></form>
</section>
```

- [ ] **步骤 4：更新聊天脚本倒计时显示**

在 `chat.js` 中读取 `data-minutes`，每秒更新 `[data-countdown]`。倒计时归零时提交 `.chat-finish` 表单。

- [ ] **步骤 5：添加聊天样式**

在 `site.css` 添加 `.chat-head`、`.timer`、`.chat-log`、`.bubble`、`.chat-input-row`、`.chat-finish`，区分参与者和人工智能消息气泡。

- [ ] **步骤 6：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_chat_page_renders_chinese_game_chat_ui
```

预期：通过。

## 任务 9：重做完成页

**文件：**

- 修改：`templates/survey/done.html`
- 修改：`static/survey/css/site.css`
- 修改：`apps/survey/tests.py`

- [ ] **步骤 1：写失败测试**

在 `apps/survey/tests.py` 中增加测试，验证完成页感谢文案和通关风格。

```python
    def test_done_page_renders_completion_card_without_answers(self):
        user = User.objects.create_user("p_done", password="pass")
        batch = ExperimentBatch.objects.create(name="批次 A", is_active=True)
        user.participant_profile.display_name = "参与者"
        user.participant_profile.batch = batch
        user.participant_profile.save()
        SurveySession.objects.create(
            user=user,
            batch=batch,
            current_session_step=SurveySession.STEP_DONE,
            batch_snapshot={},
            topic_order_snapshot=[],
            submitted_topic_order=[1, 2, 3],
        )
        self.client.force_login(user)

        response = self.client.get(reverse("survey:done"))

        self.assertContains(response, "已完成，感谢你的参与")
        self.assertContains(response, "你的每一次选择和回答都很重要")
        self.assertContains(response, "完成徽章")
        self.assertNotContains(response, "submitted_topic_order")
```

- [ ] **步骤 2：运行测试并确认失败**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_done_page_renders_completion_card_without_answers
```

预期：失败，因为完成页还很简单。

- [ ] **步骤 3：重写完成页模板**

将 `done.html` 改成通关卡：

```django
<section class="task-page task-page-done">
  {% include "survey/partials/step_header.html" %}
  <div class="completion-card">
    <div class="completion-badge" aria-label="完成徽章">完成徽章</div>
    <h1>已完成，感谢你的参与</h1>
    <p>你的每一次选择和回答都很重要。感谢你认真完成这次研究任务。</p>
    {% if outro %}<p class="outro-text">{{ outro }}</p>{% endif %}
  </div>
</section>
```

- [ ] **步骤 4：添加完成页样式**

在 `site.css` 添加 `.completion-card`、`.completion-badge`，让路线点全部显示完成态。

- [ ] **步骤 5：确保 `done` 视图传入步骤上下文**

在 `apps/survey/views.py` 的 `done` 视图中传入：

```python
return render(request, "survey/done.html", {"session": session, "outro": outro, "step_meta": _step_context("done")})
```

- [ ] **步骤 6：运行测试并确认通过**

运行：

```powershell
python manage.py test apps.survey.tests.SurveyViewTests.test_done_page_renders_completion_card_without_answers
```

预期：通过。

## 任务 10：全流程验证和浏览器检查

**文件：**

- 修改：必要时修正前面任务留下的小问题。

- [ ] **步骤 1：运行全量测试**

运行：

```powershell
python manage.py test
```

预期：全部通过。

- [ ] **步骤 2：运行系统检查**

运行：

```powershell
python manage.py check
```

预期：`System check identified no issues`。

- [ ] **步骤 3：启动本地服务**

运行：

```powershell
python manage.py runserver 127.0.0.1:8000
```

预期：本地服务可以访问。

- [ ] **步骤 4：用浏览器检查关键页面**

检查桌面宽度和窄屏宽度：

- 注册或登录页不出现英文切换。
- 第 1 站拖拽和上移 / 下移按钮可用。
- 第 3、4、8、9 站点击刻度后出现选中态。
- 第 5、7、10 站粘贴被阻止并出现中文提示。
- 完成页不展示答案。

- [ ] **步骤 5：最终状态确认**

运行：

```powershell
git status --short
```

预期：只包含本次前端实现相关文件和用户已有未提交文件；不回滚用户文件。
