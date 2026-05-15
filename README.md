# Foreign Collab Argument Quiz Site

Django 单体版研究答题网站，支持参与者登录、批次化材料、固定答题流程、中英双语展示、AI 对话接口、语音转文字接口、步骤锁定、质量事件记录，以及按批次导出 Excel/CSV。

## Local Setup

```powershell
python -m pip install -e .[dev]
python manage.py migrate
python manage.py seed_defaults
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

访问：

- 参与者端：`http://127.0.0.1:8000/survey/`
- 管理后台：`http://127.0.0.1:8000/admin/`

## Environment

复制 `.env.example` 为 `.env` 后按需调整：

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DB_ENGINE` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`
- `DUBRIFY_BASE_URL`
- `DUBRIFY_API_KEY`
- `DEFAULT_CHAT_MODEL`
- `DEFAULT_TRANSCRIBE_MODEL`

默认使用 SQLite；生产或准生产环境可切换到 PostgreSQL。

## Tests

```powershell
python manage.py test
python manage.py check
```

当前测试覆盖账号资料、批量建号、实验配置默认值、种子数据幂等性、答题状态机、质量事件、AI prompt/流式保存，以及 Excel/CSV 导出。

## Admin Workflows

1. 运行 `python manage.py seed_defaults` 创建示例批次、10 个话题、默认量表和 3 个 AI 模式。
2. 进入后台的“参与者资料”，点击“批量建号”。
3. 输入批次、初始密码和用户名列表，每行一个用户名。
4. 参与者首次登录后填写“称呼/姓名”，再进入答题流程。
5. 在“实验批次”列表点击“导出数据”，选择数据类型和 Excel/CSV 格式下载。

## Notes

- 每一步由后端状态机控制，提交后不可返回修改。
- 参与者开始后会保存批次和话题材料快照。
- 前端 JavaScript 只增强拖拽排序、评分按钮、质量事件、录音上传和流式聊天，不作为流程可信来源。
- 系统不会持久化原始音频，只保存参与者确认后的最终文本和输入方式。
