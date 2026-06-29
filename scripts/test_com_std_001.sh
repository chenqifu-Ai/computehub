#!/bin/bash
# ==============================================
# 🧪 COM-STD-001-TEST 集群跨节点通信标准 测试入口
# 用法: ./test_com_std_001.sh [--level L1,L2] [--priority P0] [--report]
# ==============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_DIR="${SCRIPT_DIR}/../reports"
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
REPORT_FILE="${REPORT_DIR}/com-std-001-test-${TIMESTAMP}.md"
JSON_REPORT="${REPORT_DIR}/com-std-001-test-${TIMESTAMP}.json"

# 默认参数
LEVEL="L2,L3"
PRIORITY="P0,P1"
GENERATE_REPORT=true
PASS_TOTAL=0
FAIL_TOTAL=0
RESULTS=()

# 解析参数
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --level) LEVEL="$2"; shift ;;
        --priority) PRIORITY="$2"; shift ;;
        --no-report) GENERATE_REPORT=false ;;
        -h|--help)
            echo "用法: ./test_com_std_001.sh [--level L1,L2] [--priority P0] [--no-report]"
            echo "  --level:    测试等级 L1|L2|L3|L4 (逗号分隔)"
            echo "  --priority: 优先级 P0|P1|P2 (逗号分隔)"
            echo "  --no-report: 不生成报告"
            exit 0
            ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
    shift
done

mkdir -p "$REPORT_DIR"

echo "============================================="
echo "🧪 COM-STD-001 集群通信标准测试"
echo "   等级: $LEVEL"
echo "   优先级: $PRIORITY"
echo "   报告: $REPORT_FILE"
echo "============================================="
echo ""

run_test_script() {
    local script="$1"
    local label="$2"
    
    if [ ! -f "$script" ]; then
        echo "  ⚠️ 脚本不存在: $script"
        RESULTS+=("{\"channel\":\"$label\",\"pass\":0,\"fail\":0,\"status\":\"skipped\"}")
        return
    fi
    
    echo ""
    echo "━━━ 🧪 $label ━━━"
    chmod +x "$script"
    
    # 跑并捕获结果
    output=$(bash "$script" 2>&1)
    exit_code=$?
    echo "$output"
    
    # 从输出解析 PASS/FAIL
    pass=$(echo "$output" | grep -oP '(?<=^PASS=)\d+' | head -1)
    fail=$(echo "$output" | grep -oP '(?<=^FAIL=)\d+' | head -1)
    pass=${pass:-0}
    fail=${fail:-0}
    
    PASS_TOTAL=$((PASS_TOTAL + pass))
    FAIL_TOTAL=$((FAIL_TOTAL + fail))
    
    if [ $exit_code -eq 0 ]; then
        RESULTS+=("{\"channel\":\"$label\",\"pass\":$pass,\"fail\":$fail,\"status\":\"passed\"}")
    else
        RESULTS+=("{\"channel\":\"$label\",\"pass\":$pass,\"fail\":$fail,\"status\":\"failed\"}")
    fi
}

# ── P0: L2 集成测试 ──
if echo "$LEVEL" | grep -q "L2"; then
    echo ""
    echo "═══ L2 集成测试 ═══"
    
    if echo "$PRIORITY" | grep -q "P0"; then
        run_test_script "${SCRIPT_DIR}/test_com_001_ssh.sh" "① SSH"
        run_test_script "${SCRIPT_DIR}/test_com_002_task.sh" "② Task API"
        run_test_script "${SCRIPT_DIR}/test_com_003_http.sh" "③ Gateway HTTP"
        run_test_script "${SCRIPT_DIR}/test_com_005_proot.sh" "⑤ AI对话"
    fi
    
    if echo "$PRIORITY" | grep -q "P1"; then
        run_test_script "${SCRIPT_DIR}/test_com_004_ws.sh" "④ WebSocket"
        run_test_script "${SCRIPT_DIR}/test_com_006_broadcast.sh" "⑥ 广播"
        run_test_script "${SCRIPT_DIR}/test_com_007_wmi.sh" "⑦ WMI"
    fi
fi

# ── L3 全链路测试 ──
if echo "$LEVEL" | grep -q "L3"; then
    echo ""
    echo "═══ L3 全链路测试 ═══"
    run_test_script "${SCRIPT_DIR}/test_com_e2e.sh" "E2E 全链路"
fi

# ── 总结果 ──
echo ""
echo "============================================="
echo "📊 测试结果汇总"
echo "   通过: $PASS_TOTAL"
echo "   失败: $FAIL_TOTAL"
echo "   总计: $((PASS_TOTAL + FAIL_TOTAL))"
echo "   通过率: $(awk "BEGIN {printf \"%.1f%%\", ($PASS_TOTAL / ($PASS_TOTAL + $FAIL_TOTAL)) * 100}")"
echo "============================================="

# ── 生成报告 ──
if [ "$GENERATE_REPORT" = true ]; then
    # JSON 报告
    echo "[" > "$JSON_REPORT"
    first=true
    for r in "${RESULTS[@]}"; do
        if [ "$first" = true ]; then first=false; else echo "," >> "$JSON_REPORT"; fi
        echo "  $r" >> "$JSON_REPORT"
    done
    echo "" >> "$JSON_REPORT"
    echo "]" >> "$JSON_REPORT"

    # Markdown 报告
    cat > "$REPORT_FILE" <<EOF
# 🧪 COM-STD-001 通信标准测试报告

时间: $(date '+%Y-%m-%d %H:%M')
执行: 入口脚本
等级: $LEVEL
优先级: $PRIORITY

## 执行摘要
- 通过: $PASS_TOTAL
- 失败: $FAIL_TOTAL
- 总计: $((PASS_TOTAL + FAIL_TOTAL))
- 通过率: $(awk "BEGIN {printf \"%.1f%%\", ($PASS_TOTAL / ($PASS_TOTAL + $FAIL_TOTAL)) * 100}")

## 通道结果
EOF

    for r in "${RESULTS[@]}"; do
        channel=$(echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['channel'])")
        status=$(echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'])")
        pass=$(echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['pass'])")
        fail=$(echo "$r" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['fail'])")
        icon="✅"
        [ "$status" != "passed" ] && icon="❌"
        [ "$status" = "skipped" ] && icon="⚠️"
        echo "- ${icon} **${channel}**: ${pass}/${pass} 通过, ${fail} 失败" >> "$REPORT_FILE"
    done

    echo "报告已生成: $REPORT_FILE"
    echo "JSON报告: $JSON_REPORT"
fi

# 通过/失败
if [ $FAIL_TOTAL -gt 0 ]; then
    echo ""
    echo "❌ 存在失败用例"
    exit 1
else
    echo ""
    echo "✅ 全部通过"
    exit 0
fi