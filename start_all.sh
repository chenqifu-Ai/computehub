#!/bin/bash
# ComputeHub - 一键启动所有服务

set -e

echo "🚀 ComputeHub 启动脚本"
echo "======================"

cd /root/GitHub/computehub

# 激活虚拟环境
source venv/bin/activate

# 1. 启动 API 服务
echo "📡 启动 API 服务..."
if ! pgrep -f "uvicorn backend.main:app" > /dev/null; then
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
    sleep 2
    echo "✅ API 服务已启动 (端口 8000)"
else
    echo "⚠️  API 服务已在运行"
fi

# 2. 启动 Node Agent（示例）
echo "🤖 启动 Node Agent..."
if ! pgrep -f "python node/agent_api.py" > /dev/null; then
    python node/agent_api.py --port 8080 &
    sleep 2
    echo "✅ Node Agent 已启动 (端口 8080)"
else
    echo "⚠️  Node Agent 已在运行"
fi

# 3. 启动 Celery Worker（需要 Redis）
echo "👷 启动 Celery Worker..."
if redis-cli ping > /dev/null 2>&1; then
    celery -A backend.workers.executor worker --loglevel=info &
    sleep 2
    echo "✅ Celery Worker 已启动"
else
    echo "⚠️  Redis 未运行，跳过 Celery Worker"
fi

# 4. 启动 Celery Beat（定时任务）
echo "⏰ 启动 Celery Beat..."
if redis-cli ping > /dev/null 2>&1; then
    celery -A backend.workers.executor beat --loglevel=info &
    sleep 2
    echo "✅ Celery Beat 已启动"
else
    echo "⚠️  Redis 未运行，跳过 Celery Beat"
fi

echo ""
echo "✅ 所有服务启动完成！"
echo ""
echo "📊 访问方式:"
echo "  - API 文档：http://localhost:8000/docs"
echo "  - Node Agent: http://localhost:8080/docs"
echo "  - 健康检查：curl http://localhost:8000/health"
echo ""
echo "🛑 停止服务:"
echo "  pkill -f 'uvicorn backend.main'"
echo "  pkill -f 'python node/agent_api'"
echo "  pkill -f 'celery'"
