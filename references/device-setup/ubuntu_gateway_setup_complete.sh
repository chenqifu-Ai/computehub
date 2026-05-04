#!/bin/bash
# Ubuntu Linux环境OpenClaw完整设置脚本

echo "🐧 Ubuntu Linux环境OpenClaw设置"
echo "📅 开始时间: $(date)"
echo "🌐 设备: 华为手机 proot Ubuntu"
echo "=================================================="

# 1. 检查Ubuntu环境
echo "🔍 检查Ubuntu环境..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- uname -a"

# 2. 检查Node.js和npm
echo "📦 检查Node.js环境..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照极速版状态: ✅ 正常 (v2.5极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31