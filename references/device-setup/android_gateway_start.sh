#!/bin/bash
# Android原生环境OpenClaw Gateway启动脚本

echo "📱 在Android原生环境启动OpenClaw Gateway"

# 1. 检查OpenClaw安装
echo "🔍 检查OpenClaw安装..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "ls -la /data/data/com.termux/files/usr/bin/openclaw 2>/dev/null || echo 'OpenClaw未安装'"

# 2. 如果未安装，则安装
echo "📦 安装OpenClaw 2026.3.13..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31