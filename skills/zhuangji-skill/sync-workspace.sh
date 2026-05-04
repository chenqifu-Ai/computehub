#!/bin/bash

# workspace同步脚本
# 用法: ./sync-workspace.sh <IP> <PORT> <USER> <PASSWORD>

set -e

IP="$1"
PORT="$2"
USER="$3"
PASSWORD="$4"

if [ $# -ne 4 ]; then
    echo "用法: $0 <IP> <PORT> <USER> <PASSWORD>"
    exit 1
fi

echo "[INFO] 开始同步workspace配置到 $USER@$IP:$PORT"

# 1. 创建目标目录结构
sshpass -p "$PASSWORD" ssh -p "$PORT" -o StrictHostKeyChecking=no "$USER@$IP" \
    "mkdir -p ~/.openclaw/workspace/{memory,scripts,config,projects}"

echo "[INFO] 目录结构创建完成"

# 2. 同步核心配置文件
echo "[INFO] 同步核心配置文件..."
sshpass -p "$PASSWORD" scp -P "$PORT" -o StrictHostKeyChecking=no \
    ~/.openclaw/workspace/AGENTS.md \
    ~/.openclaw/workspace/SOUL.md \
    ~/.openclaw/workspace/USER.md \
    ~/.openclaw/workspace/HEARTBEAT.md \
    "$USER@$IP:~/.openclaw/workspace/"

echo "[INFO] 核心配置文件同步完成"

# 3. 同步今日内存文件
echo "[INFO] 同步内存文件..."
TODAY=$(date +%Y-%m-%d)
sshpass -p "$PASSWORD" scp -P "$PORT" -o StrictHostKeyChecking=no \
    ~/.openclaw/workspace/memory/$TODAY.md \
    "$USER@$IP:~/.openclaw/workspace/memory/" 2>/dev/null || echo "今日内存文件尚未创建"

# 4. 同步配置目录
echo "[INFO] 同步配置目录..."
sshpass -p "$PASSWORD" scp -P "$PORT" -o StrictHostKeyChecking=no \
    -r ~/.openclaw/workspace/config/ \
    "$USER@$IP:~/.openclaw/workspace/" 2>/dev/null || echo "配置目录同步跳过"

echo "[INFO] workspace同步完成!"
echo "✅ 设备 $IP 已配置完成，可以正常使用"