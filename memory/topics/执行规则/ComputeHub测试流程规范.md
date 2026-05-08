# ComputeHub 测试流程规范 (STD-TEST-001)

**生效**: 2026-05-09
**版本**: v1.0
**测试脚本**: `projects/computehub/tests/test_computehub.py`
**测试结果**: 21/21 全通过 (2026-05-09 07:17)

---

## 1. 前置条件（接手时5秒检查）

```
❌ 不要重新配环境，不要重复安装
✅ 直接验证以下3项，过了就测试
```

### 1.1 网关运行
```bash
curl -s http://192.168.1.7:8282/api/health
# 预期: {"success": true, "data": "ComputeHub System Healthy"}
```

### 1.2 至少一个 Worker 在线
```bash
curl -s http://192.168.1.7:8282/api/v1/nodes/list
# 预期: data[] 不为空，status=online
```

### 1.3 测试脚本存在
```bash
ls projects/computehub/tests/test_computehub.py
```

**如果 1.1/1.2 不满足** → 跳到第 5 节「故障排查」
**如果 1.3 不存在** → 脚本已 git commit，`git checkout -- projects/computehub/tests/test_computehub.py`

---

## 2. 运行测试

```bash
cd /root/.openclaw/workspace/projects/computehub
python3 tests/test_computehub.py
```

**预期结果**: 21 项通过，0 失败（允许 WARN 和 SKIP）

### 2.1 只跑单组（调试用）
```bash
python3 tests/test_computehub.py health    # 网关健康
python3 tests/test_computehub.py tasks     # 任务生命周期
python3 tests/test_computehub.py stream    # 流式输出
python3 tests/test_computehub.py nodes     # 节点管理
python3 tests/test_computehub.py errors    # 错误处理
```

### 2.2 列出所有测试组
```bash
python3 tests/test_computehub.py --list
```

---

## 3. 测试覆盖说明

| # | 组名 | 测什么 | 失败时意味着 |
|---|------|-------|------------|
| 1 | health | 网关存活、状态接口、节点列表 | Gateway 挂了或配置错 |
| 2 | nodes | 注册/心跳/注销全流程 | 节点管理API有问题 |
| 3 | tasks | 提交→poll→完成→结果→progress→错误命令 | 核心任务流水线故障 |
| 4 | list | 任务列表统计 | 列表接口异常 |
| 5 | errors | 空参数、不存在ID | 边界处理不完善 |
| 6 | stream | 模拟Worker逐步推输出→累积验证 | progress 推送/查询链路断 |
| 7 | priority | 多优先级任务 | 调度器异常 |
| 8 | metrics | 节点指标 | Prometheus采集或接口异常 |

---

## 4. 环境现状（接手即知）

以下信息已固化，**不需要再次探测**：

### 4.1 网关
- **地址**: `http://192.168.1.7:8282`
- **进程**: `openclaw-gateway` (PID 见 `ps aux | grep gate`)
- **配置文件**: `projects/computehub/config.json`
- **当前版本**: v0.7.0

### 4.2 Worker
- **cqf-worker-02**: Windows 笔记本 LAPTOP-QOVCUVAG, i5-13500H, 16GB ✅ 在线
- **cqf-worker-01**: 192.168.1.8, H100 GPU ❌ 未接入（连旧地址 192.168.1.4:8282，需重配）

### 4.3 SSH 连接
- **1.8 没有配 SSH 免密**，需要密码。密码问老大。
- **免密密钥已存在**：`~/.ssh/id_ed25519`（没配到 1.8 而已）

### 4.4 代码
- **项目根**: `/root/.openclaw/workspace/projects/computehub`
- **Gateway 源码**: `src/gateway/gateway.go` / `gateway_worker.go`
- **Kernel 核心**: `src/kernel/actions.go` / `kernel.go`
- **Worker 二进制**: `deploy/ubuntu/bin/computehub-worker` (ARM64, 8.4MB)
- **测试代码**: `tests/test_computehub.py`

---

## 5. 故障排查链路

### 5.1 网关连不上
```bash
# 检查进程
ps aux | grep gateway

# 检查端口
netstat -tlnp | grep 8282

# 重启网关
cd /root/.openclaw/workspace/projects/computehub
./deploy/ubuntu/bin/computehub-gateway
```

### 5.2 Worker 不在线
```bash
# 检查列表
curl -s http://192.168.1.7:8282/api/v1/nodes/list

# worker-02 在 Windows 上自动注册的，gateway 启动后它应该自动连
# 如果掉了，检查 Windows 那边的 worker 进程
# worker-01 在 1.8 上需要手动重配，见 4.2（问老大密码）
```

### 5.3 任务提交失败
```bash
# 测试 task_id 是否必要
curl -s -X POST http://192.168.1.7:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"task_id":"debug-001","node_id":"cqf-worker-02","command":"echo ok"}'

# 查结果
curl -s "http://192.168.1.7:8282/api/v1/tasks/detail?task_id=debug-001&node_id=cqf-worker-02"
```

### 5.4 测试脚本报错
```bash
# 查看 Python 依赖
python3 -c "import requests" || pip install requests
```

---

## 6. 修改验证流程

改了 Gateway 或 Worker 代码后：

```bash
# 1. 改代码
# 2. 重启网关（如果需要）
# 3. 跑全部测试
python3 tests/test_computehub.py

# 4. 如果失败数比上次多 → 回退
git diff src/  # 看看改了啥

# 5. 如果全部通过 → commit
git add tests/ src/ 
git commit -m "更新: xxx - 测试全部通过"
```

---

## 7. 已知测试偏差

| 偏差 | 预期行为 | 实际行为 | 影响 |
|------|---------|---------|------|
| 空 node_id 提交任务 | 应报错 | 成功入队列 | ⚠️ 低风险（无节点可认领）|
| progress exit_code | 应返回 int | 返回 null | ⚠️ 只影响 TUI 展示 |
| node metrics 需 node_id 参数 | 可传可不传 | 必须传 | ⚠️ 文档已匹配 |

这些偏差已记录在测试脚本中（WARN 级别，非 FAIL）。

---

## 8. 测试脚本维护规范

- **不改测试预期去适配代码 bug** → 应该修 bug
- **测试脚本自身 bug** → 修完注明原因
- **新增功能必须加测试组** → 在 `TEST_GROUPS` 注册
- **每次功能变更后跑一次全测试** → 确保不 regression
