# 🚨 故障案例：盲目 Kill Worker 导致节点断联

> 时间：2026-06-23 10:15-10:30
> 责任人：端智
> 影响：wanlida-opc01 节点离线至今未恢复

---

## 📋 事件经过

**目标**：将 wanlida-opc01 的 ComputeHub Worker 加入 `--agent` 模式

**操作**：
1. 发现 worker 进程（PID 16996）没带 `--agent` 参数
2. 直接提交了 `wmic process where processid=16996 call terminate` 的 kill 任务
3. 进程被杀了，但新进程没启动起来
4. 节点 offline → ComputeHub 通道断了 → 无法远程恢复

**结果**：🔴 wanlida-opc01 离线，无法通过 ComputeHub 远程修复

---

## 🧠 根因分析

### 根本原因：**先杀再起，没有保底方案**

```
❌ 错误做法：
   kill 旧进程 → 启动新进程（串行，中间有断联窗口）

✅ 正确做法：
   先 spawn 新进程（test-register 模式）→ 验证新进程在线 → 再杀旧进程
```

### 具体问题

| 问题 | 说明 |
|------|------|
| **唯一通道依赖** | ComputeHub 是唯一通道，kill worker = 自断通信 |
| **没有 fallback** | 没准备备用入口（如 SSH、计划任务自动重启） |
| **串行操作** | kill 和 spawn 之间有空窗期，一旦 spawn 失败就断联 |
| **没验证 kill 结果** | `wmic` 命令在 worker shell 里执行，实际没找到（`/bin/sh: wmic: not found`），但进程确实被杀了 |

---

## 📌 教训总结

### 铁律：**杀进程前，先想好怎么接上**

```
🔍 动手前三思（这次全没做到）：
① 为什么做？→ 加 --agent 参数
② 影响谁？→ wanlida-opc01 整个节点
③ 失败预案？→ ❌ 没有！kill 完就断联了
```

### 正确流程（以后必须遵守）

```
1. 先 spawn 新进程（带 --agent 参数）
2. 验证新进程在 ComputeHub 上注册成功
3. 确认新进程心跳正常
4. 再杀旧进程
5. 验证节点状态保持 online
```

### 对于 Windows 节点的特殊注意事项

- `wmic` 在 ComputeHub worker shell 里可能找不到（路径问题）
- 杀进程后 Windows 计划任务可能不会自动重启
- 最好通过计划任务管理：`schtasks /End` + `schtasks /Run` 而不是直接 kill
- 或者用 `taskkill /PID` 更可靠

---

## ✅ 修复方案（等节点恢复后执行）

1. 等 wanlida-opc01 自动恢复（或老大手动重启 worker）
2. 用 `schtasks /Run` 或 `wmic process call create` 启动带 `--agent` 的新进程
3. 验证 Agent 注册成功

---

*本案例已同步至 ComputeHub 共享记忆层，所有 Agent 可查询。*
