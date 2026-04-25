# 🔧 系统稳定化方案

**制定时间**: 2026-04-25 09:50
**制定人**: 小智
**紧急程度**: 🔴 高危 — 系统内存仅剩 135MB，随时 OOM

---

## 一、问题诊断

### 当前危机
1. **物理内存仅剩 135MB** — 极度危险
2. **Swap 已用 6.2G** — 系统严重依赖虚拟内存
3. **负载 19-21** — 高（proot 环境可能虚高，但内存是真实的）
4. **多个 cron 在高频轮询** — 浪费资源

### 根因分析
- 大量 cron job 在后台运行，即使已禁用，之前累积的错误和重试可能还在影响系统
- 模型测试任务（qwen3.6-35b 测试 v1-v6）消耗大量内存
- Ollama 服务 + 本地模型占用内存
- 多个 exec 任务并发执行

---

## 二、执行方案（按优先级排序）

### 🔴 紧急：立即执行（现在）

#### 1. 清理 Swap（释放内存）
```bash
# 回收不活跃内存
sync && echo 3 > /proc/sys/vm/drop_caches
# 如果 swap 使用严重，可以考虑暂停并恢复
# swapoff -a && swapon -a  (谨慎使用，会导致短暂卡顿)
```

#### 2. 禁用所有非必要的 cron job
```bash
# 已禁用：openclaw-research-progress-report（每5分钟，42次错误）
# 已禁用：Computehub 状态监控（每30分钟，报错）

# 需要禁用的：
# - 所有"每10分钟学习"类型的 cron（已禁用 ✅）
# - 所有股票监控 cron（已禁用 ✅）
# - 公司脉搏相关（已禁用 ✅）
```

**保留的 cron（每天一次，低风险）：**
- 财神爷财务分析（0 11 * * *）✅ 保留
- 法海风险评估（0 12 * * *）✅ 保留
- 公司脉搏报告-下午（0 15 * * *）✅ 保留
- 百炼用量日报（0 20 * * *）✅ 保留
- 每日投资汇报（0 20 * * *）✅ 保留
- 股票持仓每日提醒（0 8 * * 1-5）✅ 保留

#### 3. 清理临时文件和日志
```bash
# 清理 ai_agent/results/ 下的旧日志
cd /root/.openclaw/workspace
# 备份 conversation_debug.jsonl（已创建查看器）
# 清理过大的日志文件
find /root/.openclaw/workspace -name "*.log" -size +10M -exec rm -f {} \;
find /root/.openclaw/workspace -name "*.tmp" -delete
```

#### 4. 检查并停止高内存进程
```bash
# 查看占用内存最多的进程
ps aux --sort=-%mem | head -15
# 如果有非必要的 Python 进程，考虑停止
```

### 🟡 短期：今天内执行

#### 5. 优化 Ollama 配置
- 减少加载的模型数量（从 8 个减少到 2-3 个核心模型）
- 当前加载的模型：qwen2.5:3b, qwen2.5:latest, glm-4.7-flash, qwen:0.5b, Llama3.1, ministral-3:8b, gemma3:4b, deepseek-coder:6.7b
- 建议保留：glm-4.7-flash（最轻量）+ 需要时按需加载

#### 6. 清理磁盘空间（79% → <70%）
```bash
# 清理 references/other/ 下未分类的 94 个文件
# 清理 ai_agent/code/ 下不需要的脚本
# 清理旧的记忆文件
```

#### 7. 调整 Cron 调度策略
**原则：**
- 频率 ≤ 每天 1 次
- 避免并发执行
- 错误次数 > 3 自动暂停

**具体调整：**
- 财务分析、风险评估、投资汇报 → 保留（每天一次）
- 公司脉搏 → 改为每天 1 次（上午/下午各一次）
- 股票监控 → 保留持仓提醒（每天一次）
- 所有"每X分钟"的学习任务 → 全部禁用
- 所有股票盘前/盘中/尾盘监控 → 全部禁用

### 🟢 中期：本周执行

#### 8. 建立系统健康检查机制
- 创建 `scripts/system-health-check.sh` 脚本
- 监控内存使用，超过 80% 自动告警
- 监控 Swap 使用，超过 50% 自动告警
- 监控磁盘使用，超过 85% 自动清理

#### 9. 优化模型配置
- 区分"本地模型"和"云端模型"
- 本地模型只加载最需要的 2-3 个
- 复杂任务使用云端模型（Qwen API / Ollama 云端）

#### 10. 建立资源使用规范
- 每个 cron job 必须设置 `timeoutSeconds`
- 每个 cron job 必须设置 `consecutiveErrors` 阈值
- 超过阈值的 job 自动暂停

---

## 三、执行命令清单

### 立即执行：
```bash
# 1. 查看当前内存占用详情
free -h && echo "---" && cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|SwapUsed"

# 2. 查看进程内存占用 Top 15
ps aux --sort=-%mem | head -15

# 3. 回收页面缓存
sync && echo 3 > /proc/sys/vm/drop_caches

# 4. 检查磁盘大文件
find /root/.openclaw/workspace -type f -size +50M -exec ls -lh {} \; 2>/dev/null | sort -k5 -h -r | head -10

# 5. 清理临时文件
find /root/.openclaw/workspace -name "*.tmp" -delete
find /root/.openclaw/workspace -name "*.bak" -delete
```

### 今天内执行：
```bash
# 6. 清理 references/other/ 下未分类文件（需要老大确认）
ls -la /root/.openclaw/workspace/references/other/

# 7. 减少 Ollama 加载的模型
# 先查看当前模型
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# 8. 创建系统健康检查脚本
cat > /root/.openclaw/workspace/scripts/system-health-check.sh << 'EOF'
#!/bin/bash
# 系统健康检查脚本
echo "=== 系统健康检查 $(date '+%Y-%m-%d %H:%M:%S') ==="

# 内存检查
MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))
echo "内存: ${MEM_USED}MB/${MEM_TOTAL}MB (${MEM_PERCENT}%) 可用:${MEM_AVAIL}MB"

# Swap 检查
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')
if [ "$SWAP_TOTAL" -gt 0 ]; then
    SWAP_PERCENT=$((SWAP_USED * 100 / SWAP_TOTAL))
    echo "Swap: ${SWAP_USED}MB/${SWAP_TOTAL}MB (${SWAP_PERCENT}%)"
fi

# 磁盘检查
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}')
DISK_PERCENT=$(echo $DISK_USAGE | sed 's/%//')
echo "磁盘: ${DISK_USAGE}"

# 负载检查
LOAD=$(cat /proc/loadavg | awk '{print $1}')
echo "负载: ${LOAD}"

# 告警
if [ "$MEM_PERCENT" -gt 90 ]; then
    echo "🔴 严重: 内存使用超过 90%!"
elif [ "$MEM_PERCENT" -gt 80 ]; then
    echo "🟡 警告: 内存使用超过 80%"
fi

if [ "$DISK_PERCENT" -gt 90 ]; then
    echo "🔴 严重: 磁盘使用超过 90%!"
elif [ "$DISK_PERCENT" -gt 80 ]; then
    echo "🟡 警告: 磁盘使用超过 80%"
fi

echo "=== 检查完成 ==="
EOF
chmod +x /root/.openclaw/workspace/scripts/system-health-check.sh
```

---

## 四、执行顺序建议

```
步骤 0: 确认方案 (老大审核)
  ↓
步骤 1: 回收内存 + 清理 Swap  ← 现在执行
  ↓
步骤 2: 确认 Cron 精简清单   ← 需要老大确认
  ↓
步骤 3: 执行 cron 禁用       ← 已执行 ✅
  ↓
步骤 4: 清理临时文件         ← 待执行
  ↓
步骤 5: 检查大文件并清理     ← 待执行
  ↓
步骤 6: 优化 Ollama 模型     ← 待执行
  ↓
步骤 7: 创建健康检查脚本     ← 待执行
  ↓
步骤 8: 验证系统稳定         ← 待执行
```

---

## 五、需要老大确认的事项

1. **是否现在执行内存回收？**（会短暂影响系统响应）
2. **Cron 精简方案是否接受？**（只保留每天一次的 6 个）
3. **是否清理 references/other/ 下 94 个未分类文件？**
4. **是否减少 Ollama 加载的模型数量？**（从 8 个减到 2-3 个）
5. **是否删除不需要的旧脚本和日志？**

---

## 六、预防措施

### 系统稳定规则（写入 AGENTS.md）
1. 内存使用 > 80% 时，暂停所有非必要的自动化任务
2. Swap 使用 > 50% 时，立即清理临时文件
3. 每个 cron 必须设置 timeout（建议 120 秒）
4. 连续错误 > 3 次的 cron 自动暂停，等待人工处理
5. 磁盘使用 > 85% 时，启动自动清理流程

### Cron 管理规范
1. **频率限制**：所有 cron 不超过每天 1 次
2. **超时限制**：所有 cron 必须设置 timeoutSeconds ≤ 120
3. **错误限制**：consecutiveErrors > 3 自动暂停
4. **审批流程**：新增 cron 需要确认不影响系统稳定

---

**制定人**: 小智 🤖
**日期**: 2026-04-25 09:50
**状态**: ⏳ 等待老大确认
