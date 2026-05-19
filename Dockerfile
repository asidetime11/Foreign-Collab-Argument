FROM python:3.12-slim

# 设置环境变量，确保 Python 输出直接打印到控制台，不进行缓存
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 替换 Debian 软件源为阿里云镜像，并安装编译依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存机制加速后续构建
COPY pyproject.toml .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -e . gunicorn uvicorn[standard]

# 复制项目其余所有代码
COPY . .

# 收集 Django 静态文件
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
