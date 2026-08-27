# Docker Port Hub - 后端镜像
FROM python:3.11-slim

# 安装 docker CLI（用于容器检测）
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 配置文件目录
RUN mkdir -p /app/config

EXPOSE 38082

CMD ["python", "app.py"]