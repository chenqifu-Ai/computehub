# 🎯 自我监控技能

## 📋 技能描述
实时监控长时间运行任务的状态，自动检测异常并自我纠正。

## 🚀 使用场景
- 编译、构建等长时间任务
- 服务部署和启动
- 任何需要持续监控的过程

## 🔧 核心方法

### 📊 基础监控命令
```bash
# 进程监控
ps aux | grep -E '(进程关键词)' | grep -v grep

# CPU/内存监控
top -n 1 -b | head -15

# 循环监控
for i in {1..10}; do
    echo "=== 监控检查 $i ==="
    ps aux | grep -E '(关键词)' | grep -v grep
    top -n 1 -b | grep '进程名' | head -1
    sleep 5
done
```

### 🎯 编译任务监控示例
```bash
# 监控TypeScript编译
sshpass -p 密码 ssh -p 端口 用户@IP地址 \
  "for i in {1..12}; do  # 监控1分钟(12*5秒)
     echo '=== 编译监控检查 $i ===';
     ps aux | grep -E '(node.*tsc|pnpm|build)' | grep -v grep;
     top -n 1 -b | grep 'node.*tsc' | head -1;
     echo '---';
     sleep 5;
   done"
```

### ⚠️ 异常检测指标
- **进程消失**: 监控进程不存在
- **CPU闲置**: 进程CPU使用率为0
- **内存异常**: 内存使用持续增长不释放
- **超时**: 任务执行时间过长

### 🔄 自我纠正策略
1. **进程重启**: 如果进程消失，重新启动
2. **资源清理**: 内存过高时清理缓存
3. **超时处理**: 设置超时限制，超时后重启
4. **日志分析**: 检查错误日志并相应处理

## 📁 文件位置
- **技能目录**: `~/.openclaw/workspace/skills/self-monitoring/`
- **监控脚本**: `scripts/monitor-task.sh`

## 🎯 最佳实践
1. **定期监控**: 每5-10秒检查一次
2. **多重指标**: 检查进程、CPU、内存、磁盘IO
3. **超时设置**: 为长任务设置合理超时
4. **错误处理**: 自动识别常见错误模式
5. **状态报告**: 定期向用户报告进度

## 💡 使用示例
```bash
# 监控编译任务
./scripts/monitor-task.sh \
  --process "node.*tsc" \
  --timeout 600 \
  --check-interval 5 \
  --max-checks 120
```

---
**创建时间**: 2026-04-05
**更新者**: 小智
**目的**: 实现任务自我监控和自动纠正