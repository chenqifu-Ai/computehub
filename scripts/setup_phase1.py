#!/usr/bin/env python3
"""ComputeHub v2.0 MVP - Phase 1: 基础设施"""
import os, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

def create_file(path, content=""):
    full_path = BASE / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content.lstrip("\n"))
    print(f"  ✅ {path}")

# ============================
# 1. requirements.txt
# ============================
create_file("requirements.txt", """
fastapi==0.136.0
uvicorn==0.46.0
sqlalchemy[asyncio]==2.0.49
asyncpg==0.30.0
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.5.0
python-multipart==0.0.26
celery[redis]==5.6.3
redis==5.2.1
pyyaml==6.0.3
pydantic==2.11.0
pydantic-settings==2.8.0
httpx==0.28.1
greenlet==3.4.0
""")

# ============================
# 2. config.yaml
# ============================
create_file("config.yaml", """
database:
  url: "sqlite+aiosqlite:///./computehub.db"
gateway:
  host: "0.0.0.0"
  port: 8000
  workers: 4
auth:
  secret_key: "change-me-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 1440
executor:
  timeout_seconds: 300
  sandbox_path: "/tmp/computehub"
""")

# ============================
# 3. .env.example
# ============================
create_file(".env.example", """
# ComputeHub 环境变量配置
COMPUTEHUB_DATABASE_URL=sqlite+aiosqlite:///./computehub.db
COMPUTEHUB_PORT=8000
COMPUTEHUB_SECRET_KEY=change-me-in-production
COMPUTEHUB_REDIS_URL=redis://localhost:6379/0
""")

# ============================
# 4. Dockerfile
# ============================
create_file("Dockerfile", """
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

# ============================
# 5. docker-compose.yml
# ============================
create_file("docker-compose.yml", """
version: '3.8'

services:
  app:
    build: .
    ports:
      - "${COMPUTEHUB_PORT:-8000}:8000"
    environment:
      - COMPUTEHUB_DATABASE_URL=sqlite+aiosqlite:///./computehub.db
      - COMPUTEHUB_SECRET_KEY=dev-secret-key-change-in-production
    volumes:
      - ./computehub.db:/app/computehub.db
    command: >
      sh -c "python -c 'from src.core.database import engine, Base; import src.models; Base.metadata.create_all(bind=engine)' && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

  worker:
    build: .
    environment:
      - COMPUTEHUB_DATABASE_URL=sqlite+aiosqlite:///./computehub.db
      - COMPUTEHUB_SECRET_KEY=dev-secret-key-change-in-production
      - COMPUTEHUB_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./computehub.db:/app/computehub.db
      - /tmp/computehub-sandbox:/tmp/computehub-sandbox
    command: celery -A src.workers.task_worker worker --loglevel=info
    depends_on:
      - redis
    profiles:
      - worker

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    profiles:
      - worker
""")

# ============================
# 6. .gitignore
# ============================
create_file(".gitignore", """
__pycache__/
*.pyc
*.pyo
*.db
*.log
*.pid
.env
venv/
.computehub/
/tmp/computehub-sandbox/
""")

print("\n✅ Phase 1 基础设施文件创建完成！")
