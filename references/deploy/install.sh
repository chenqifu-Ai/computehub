#!/bin/bash
# 语音交互一键安装

echo "安装必要工具..."
sudo apt update
sudo apt install -y espeak ffmpeg python3

echo "设置完成!"
echo "运行: python3 voice_core.py"
