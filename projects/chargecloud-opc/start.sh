#!/bin/bash
# ChargeCloud OPC - AI 智能体管理系统启动脚本
# 创建时间：2026-04-19

set -e

PROJECT_ROOT="/root/.openclaw/workspace/projects/chargecloud-opc"
FRAMEWORK_DIR="$PROJECT_ROOT/framework"
LOG_DIR="$PROJECT_ROOT/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "============================================================"
echo "🤖 ChargeCloud OPC - AI 智能体管理系统"
echo "============================================================"
echo "项目根目录：$PROJECT_ROOT"
echo "框架目录：$FRAMEWORK_DIR"
echo "日志目录：$LOG_DIR"
echo "启动时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""

# 检查参数
case "$1" in
    start)
        echo "🚀 启动完整系统..."
        cd "$FRAMEWORK_DIR"
        python3 main.py
        ;;
    
    test)
        echo "🧪 测试模式..."
        cd "$FRAMEWORK_DIR"
        python3 main.py --test
        ;;
    
    status)
        echo "📊 系统状态..."
        cd "$FRAMEWORK_DIR"
        python3 main.py --status
        ;;
    
    daily)
        echo "📋 执行日常运营..."
        cd "$FRAMEWORK_DIR"
        python3 main.py --daily
        ;;
    
    decision)
        if [ -z "$2" ]; then
            echo "❌ 请提供决策议题"
            echo "用法：$0 decision \"议题内容\""
            exit 1
        fi
        echo "🎯 执行重大决策：$2"
        cd "$FRAMEWORK_DIR"
        python3 main.py --decision "$2"
        ;;
    
    *)
        echo "用法：$0 {start|test|status|daily|decision}"
        echo ""
        echo "命令说明:"
        echo "  start    - 启动完整系统（持续运行）"
        echo "  test     - 测试模式（快速验证）"
        echo "  status   - 查看系统状态"
        echo "  daily    - 执行日常运营工作流"
        echo "  decision - 执行重大决策工作流"
        echo ""
        echo "示例:"
        echo "  $0 start              # 启动系统"
        echo "  $0 test               # 测试模式"
        echo "  $0 status             # 查看状态"
        echo "  $0 daily              # 执行日常运营"
        echo "  $0 decision \"是否扩大规模\"  # 重大决策"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "✅ 操作完成"
echo "============================================================"
