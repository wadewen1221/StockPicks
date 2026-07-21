# 后端 Dockerfile
# 基于 Python 3.12 官方镜像（轻量、锁版本）
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 系统依赖（akshare/pandas/numpy 在 Linux 上需要的底层库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（利用 Docker 缓存，requirements 没变就不重装）
COPY requirements.txt .

# 升级 pip + 安装依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 创建必要目录（数据 / 日志 / 测试临时目录）
RUN mkdir -p /app/data/historical /app/data/fiscal /app/backend/logs

# 环境变量默认值（可被 docker-compose 覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5001 \
    HOST=0.0.0.0 \
    DEBUG=false \
    STOCK_PICKS_DATA=/app/data/historical \
    STOCK_PICKS_FISCAL=/app/data/fiscal

# 暴露端口
EXPOSE 5001

# 健康检查（5 秒探一次，连续 3 次失败视为不健康）
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

# 启动命令
WORKDIR /app/backend
CMD ["python", "main.py"]