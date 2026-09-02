# Cyber-Roaster 后端镜像
FROM python:3.10-slim

# 设置工作目录与缓冲环境变量
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 先安装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY app ./app

# 暴露 FastAPI 端口
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
