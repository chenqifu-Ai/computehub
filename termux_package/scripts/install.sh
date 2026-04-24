#!/bin/bash
# Termux OpenClaw 安装脚本

echo "正在安装 OpenClaw 环境..."

# 更新包管理器
pkg update -y
pkg upgrade -y

# 安装必要软件
pkg install -y python nodejs git curl wget openssh

# 安装 OpenClaw
npm install -g @openclaw/cli

# 创建配置目录
mkdir -p ~/.openclaw/workspace

# 复制配置文件
echo "配置复制完成"

# 启动 OpenClaw
openclaw gateway start &

echo "✅ OpenClaw 安装完成"
echo "访问地址: http://localhost:18789"
