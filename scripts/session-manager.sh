#!/bin/bash

# OpenClaw 会话管理工具
# 用法：
#   session-manager.sh save <name>     - 保存当前会话快照
#   session-manager.sh list            - 列出所有保存的快照
#   session-manager.sh info <name>     - 查看快照信息
#   session-manager.sh export <name>   - 导出快照到文本文件

SNAPSHOTS_DIR="$HOME/.openclaw/workspace/sessions"
MEMORY_DIR="$HOME/.openclaw/workspace/memory"

mkdir -p "$SNAPSHOTS_DIR"

save_session() {
    local name="$1"
    local timestamp=$(date +%Y-%m-%d_%H%M%S)
    local snapshot_file="$SNAPSHOTS_DIR/${name}_${timestamp}.md"
    
    # 获取最新的会话文件
    local latest_session=$(ls -t ~/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null | head -1)
    
    if [ -z "$latest_session" ]; then
        echo "❌ 没有找到活跃会话"
        exit 1
    fi
    
    # 提取会话关键信息
    local session_id=$(basename "$latest_session" .jsonl)
    local total_lines=$(wc -l < "$latest_session")
    
    # 生成快照文件
    cat > "$snapshot_file" <<EOF
# 会话快照：${name}

**保存时间**：$(date '+%Y-%m-%d %H:%M:%S')
**会话ID**：${session_id}
**消息数量**：${total_lines}

---

## 会话上下文

EOF
    
    # 提取关键决策和上下文（简化版）
    echo "正在提取会话关键信息..."
    
    # 提取用户消息和关键内容
    jq -r 'select(.type == "message" and .message.role == "user") | .message.content[].text // empty' "$latest_session" 2>/dev/null | \
        head -20 >> "$snapshot_file" || echo "无法提取消息" >> "$snapshot_file"
    
    # 创建会话信息摘要
    local info_file="$SNAPSHOTS_DIR/.info/${name}.json"
    mkdir -p "$SNAPSHOTS_DIR/.info"
    
    cat > "$info_file" <<EOF
{
  "name": "$name",
  "timestamp": "$timestamp",
  "session_file": "$latest_session",
  "session_id": "$session_id",
  "total_lines": $total_lines
}
EOF
    
    echo "✅ 会话快照已保存：$snapshot_file"
    echo "📄 快照信息：$info_file"
}

list_sessions() {
    echo "📋 已保存的会话快照："
    echo ""
    
    if [ ! -d "$SNAPSHOTS_DIR/.info" ] || [ -z "$(ls -A $SNAPSHOTS_DIR/.info 2>/dev/null)" ]; then
        echo "  （暂无快照）"
        return
    fi
    
    for info_file in "$SNAPSHOTS_DIR/.info"/*.json; do
        if [ -f "$info_file" ]; then
            local name=$(cat "$info_file" | grep -o '"name"[^,]*' | cut -d'"' -f4)
            local timestamp=$(cat "$info_file" | grep -o '"timestamp"[^,]*' | cut -d'"' -f4)
            local lines=$(cat "$info_file" | grep -o '"total_lines"[^,}]*' | grep -o '[0-9]*')
            echo "  📁 $name"
            echo "     时间：$timestamp"
            echo "     消息数：$lines"
            echo ""
        fi
    done
}

info_session() {
    local name="$1"
    local info_file="$SNAPSHOTS_DIR/.info/${name}.json"
    
    if [ ! -f "$info_file" ]; then
        echo "❌ 找不到快照：$name"
        exit 1
    fi
    
    echo "📄 会话快照信息："
    echo ""
    jq '.' "$info_file"
    echo ""
    echo "快照文件："
    ls -lh "$SNAPSHOTS_DIR/${name}_"*.md 2>/dev/null || echo "  （快照文件不存在）"
}

export_session() {
    local name="$1"
    local info_file="$SNAPSHOTS_DIR/.info/${name}.json"
    
    if [ ! -f "$info_file" ]; then
        echo "❌ 找不到快照：$name"
        exit 1
    fi
    
    local session_file=$(jq -r '.session_file' "$info_file")
    local export_file="$HOME/openclaw-session-${name}_$(date +%Y%m%d).txt"
    
    echo "📤 导出会话到：$export_file"
    
    # 转换 JSONL 为可读文本
    jq -r '
        if .type == "message" then
            "【\(.message.role)】\(.message.content[].text // .message.content // empty)"
        elif .type == "session" then
            "# 会话开始：\(.id)"
        else
            empty
        end
    ' "$session_file" 2>/dev/null > "$export_file" || {
        echo "❌ 导出失败"
        exit 1
    }
    
    echo "✅ 导出成功！"
    echo "📄 文件位置：$export_file"
    echo "📊 大小：$(wc -l < "$export_file") 行"
}

# 主逻辑
case "$1" in
    save)
        if [ -z "$2" ]; then
            echo "用法: $0 save <名称>"
            exit 1
        fi
        save_session "$2"
        ;;
    list)
        list_sessions
        ;;
    info)
        if [ -z "$2" ]; then
            echo "用法: $0 info <名称>"
            exit 1
        fi
        info_session "$2"
        ;;
    export)
        if [ -z "$2" ]; then
            echo "用法: $0 export <名称>"
            exit 1
        fi
        export_session "$2"
        ;;
    *)
        echo "OpenClaw 会话管理工具"
        echo ""
        echo "用法:"
        echo "  $0 save <name>      保存当前会话快照"
        echo "  $0 list             列出所有快照"
        echo "  $0 info <name>      查看快照详细信息"
        echo "  $0 export <name>    导出快照为文本文件"
        ;;
esac