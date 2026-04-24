# 股票交易软件 - Docker部署

FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY strategies/ ./strategies/

# 创建数据目录
RUN mkdir -p /app/backend/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "backend/main.py"]