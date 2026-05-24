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

## Server Deployment

项目使用 Docker Compose 部署，包含 Django/Gunicorn 应用容器和 Nginx 反向代理容器。

### 前置条件

- 服务器已安装 Docker 和 Docker Compose
- 已将代码克隆到服务器

### 部署步骤

**1. 准备环境变量**

```bash
cp .env.example .env
```

编辑 `.env`，至少设置以下生产环境配置：

```env
DJANGO_SECRET_KEY=<随机长字符串>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=foreign-collab.com,www.foreign-collab.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://foreign-collab.com,https://www.foreign-collab.com
DJANGO_SESSION_COOKIE_SECURE=1
DJANGO_CSRF_COOKIE_SECURE=1
```

如果你暂时还没有配置 HTTPS 证书，可先将 `DJANGO_CSRF_TRUSTED_ORIGINS` 改成：

```env
DJANGO_CSRF_TRUSTED_ORIGINS=http://foreign-collab.com,http://www.foreign-collab.com
```

**2. 构建并启动服务**

```bash
docker compose up -d --build
```

首次启动后执行数据库初始化：

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_defaults
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py check --deploy
```

**3. 访问服务**

- 参与者端：`http://foreign-collab.com/survey/`
- 管理后台：`http://foreign-collab.com/admin/`

### 域名上线检查

- 确认 `foreign-collab.com` 和 `www.foreign-collab.com` 的 DNS A 记录都指向当前服务器公网 IP。
- 确认服务器安全组 / 防火墙已放行 `80` 端口；若后续启用 HTTPS，还需放行 `443`。
- 修改完配置后执行：

```bash
cp .env.example .env
docker compose up -d --build
docker compose restart nginx web
```

- 可使用以下命令验证响应头中的域名是否正确：

```bash
curl -I http://foreign-collab.com
curl -I http://foreign-collab.com/admin/
```

### 架构说明

| 容器 | 镜像 | 说明 |
|------|------|------|
| `web` | 本地构建（`python:3.12-slim`） | Gunicorn + UvicornWorker，监听 8000 端口 |
| `nginx` | `nginx:alpine` | 反向代理，对外暴露 80 端口，同时提供静态文件服务 |

数据持久化通过两个 Docker volume 实现：
- `sqlite_data`：SQLite 数据库文件（挂载到 `/app/data/`）
- `static_files`：Django 静态文件（`collectstatic` 输出）

### 常用运维命令

```bash
# 查看日志
docker compose logs -f web

# 重启服务
docker compose restart web

# 更新代码后重新部署
git pull
docker compose up -d --build

# 备份数据库
docker compose cp web:/app/data/db.sqlite3 ./backup_$(date +%Y%m%d).sqlite3
```

## Notes

- 每一步由后端状态机控制，提交后不可返回修改。
- 参与者开始后会保存批次和话题材料快照。
- 前端 JavaScript 只增强拖拽排序、评分按钮、质量事件、录音上传和流式聊天，不作为流程可信来源。
- 系统不会持久化原始音频，只保存参与者确认后的最终文本和输入方式。
- 若启用语音转文字，请在后台“模型和 API”的对应 Key 支持模型中加入 `whisper-1`，并保持 `DEFAULT_TRANSCRIBE_MODEL=whisper-1`。
