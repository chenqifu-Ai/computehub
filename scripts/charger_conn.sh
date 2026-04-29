#!/bin/bash
# 充电桩批量插枪工具 (IMG-REC-001)
# 用法: ./charger_conn.sh 桩号1 桩号2 ... [base_url]

BASE_URL="${3:-http://47.93.134.184:9001}"
GUN_NO="${2:-2}"
GROUP_SIZE=5

echo "=========================================="
echo "  充电桩批量插枪工具"
echo "  桩号: ${1}"
echo "  枪号: ${GUN_NO}"
echo "  批次大小: ${GROUP_SIZE}"
echo "=========================================="

if [ $# -lt 1 ]; then
    echo "用法: $0 桩号1 桩号2 ... [base_url]"
    echo "  默认枪号: 2"
    echo "  默认批次: 5个一组"
    exit 1
fi

# 将所有桩号存入数组
STAKES=()
for stake in "$@"; do
    STAKES+=("$stake")
done

TOTAL=${#STAKES[@]}
echo "共 ${TOTAL} 个桩号，分为 $(( (TOTAL + GROUP_SIZE - 1) / GROUP_SIZE )) 个批次"
echo ""

# 分批处理
for ((i=0; i<TOTAL; i+=GROUP_SIZE)); do
    batch_num=$(( i/GROUP_SIZE + 1 ))
    end=$((i + GROUP_SIZE))
    if [ $end -gt $TOTAL ]; then end=$TOTAL; fi
    
    echo "--- 批次 ${batch_num}: 桩号 ${i}~$((end-1)) ---"
    
    for ((j=i; j<end; j++)); do
        stake="${STAKES[$j]}"
        result=$(curl -s -X POST "${BASE_URL}/conn" \
            -F "stakeId=${stake}" \
            -F "gunNo=${GUN_NO}" 2>&1)
        
        if [[ "$result" == *"成功"* ]]; then
            echo "  ✅ ${stake} → 插枪成功"
        else
            echo "  ❌ ${stake} → 失败: ${result}"
        fi
    done
    
    echo ""
done

echo "=========================================="
echo "  全部完成，共 ${TOTAL} 个桩号"
echo "=========================================="
