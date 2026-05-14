#!/bin/bash
# ComputeHub 视频生产任务 - shell wrapper
# 通过 Gateway 提交视频生产任务到指定节点
# 用法: bash computehub_producer.sh <topic> [style] [output_path]

set -e

GATEWAY="${GATEWAY:-http://192.168.1.12:8282}"
TOPIC="${1:-AI改变生活}"
STYLE="${2:-tech}"
OUTPUT="${3:-/tmp/video_output.mp4}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. 先用 LLM 生成文案（本地或者远程）
# 这里用简单的预设文案，后面可接 composer 的 LLM 生成

generate_script() {
    local topic="$1"
    cat <<EOF
今天我们来聊聊：${topic}。

这是一个全新的时代，技术正在以惊人的速度改变着我们的世界。

让我们一起拥抱变化，创造未来。

感谢您的观看。
EOF
}

SCRIPT=$(generate_script "$TOPIC")

echo "📌 主题: $TOPIC"
echo "🎨 风格: $STYLE"
echo "📝 文案长度: $(echo "$SCRIPT" | wc -c)字符"

# 2. 在本地跑视频合成（redmi-1 节点）
python3 "$SCRIPT_DIR/produce_video.py" \
    --topic "$TOPIC" \
    --script "$SCRIPT" \
    --style "$STYLE" \
    --output "$OUTPUT" \
    --json 2>&1

echo ""
echo "✅ 通过 ComputeHub 提交完成"
echo "📁 输出: $OUTPUT"
