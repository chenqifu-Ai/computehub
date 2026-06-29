# DEPLOY-STD-001: Gateway Binary 部署验证标准流程

**版本**: v1.0  
**创建日期**: 2026-06-05  
**起因**: v1.3.15 Gallery-Only 事故（核心路由全部丢失，集群瘫痪6分钟）  
**适用范围**: ECS Gateway 及所有 Worker 节点的 binary 替换/升级操作

---

## 1. 📋 核心原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **先验证，再替换** | 新 binary 必须通过路由完整性测试才能上线 |
| 2 | **保留回滚** | 旧版完整 binary 必须在 `deploy/` 目录中留存，作为回滚点 |
| 3 | **全量编译** | Gateway 是"所有子系统的宿主"，编译时必须包含全部模块 |
| 4 | **分步替换** | 先停旧 → 验证新 → 再停备份 → 不要一次性删除所有副本 |

---

## 2. 🧪 路由完整性测试脚本

```bash
#!/bin/bash
# gatecheck.sh — Gateway 路由完整性测试
# 用法: ./gatecheck.sh <gateway_url>
# 示例: ./gatecheck.sh http://36.250.122.43:8282

GW=${1:-"http://36.250.122.43:8282"}
FAIL=0

# 核心路由清单
ROUTES=(
  "/api/v1/tasks/list"
  "/api/v1/tasks/submit"
  "/api/v1/nodes/list"
  "/api/v1/nodes/register"
  "/api/v1/agent/stream"
  "/api/v1/download"
  "/api/v1/gallery/files"
  "/api/v1/gallery/upload"
  "/api/v1/composer/generate"
)

echo "🔍 Gateway 路由完整性测试: $GW"
echo "=================================="

for route in "${ROUTES[@]}"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$GW$route" 2>/dev/null)
  if [ "$CODE" = "200" ] || [ "$CODE" = "405" ]; then
    echo "  ✅ $route → $CODE"
  else
    echo "  ❌ $route → $CODE (FAIL)"
    FAIL=1
  fi
done

echo "=================================="
if [ $FAIL -eq 0 ]; then
  echo "✅ 全部 ${#ROUTES[@]} 条路由通过"
else
  echo "❌ 有路由未通过，禁止上线此 binary"
fi
exit $FAIL
```

**要求**: 全部路由返回 `200` 或 `405`（方法不允许也算路由注册成功）。出现任何其他状态码 → **不准部署**。

---

## 3. 🏗️ 编译前置检查

编译前确认以下条件：

```bash
# 1. 确保 build tags 包含全模块（无限制性 tag）
go build -v ./cmd/computehub

# 2. 检查 binary 大小是否合理
#    Gallery-only: ~8-10MB
#    完整 Gateway: ~12-16MB+
#    如果小于 10MB，高度怀疑缺失模块
ls -lh computerhub

# 3. 快速检查是否包含关键符号
strings computerhub | grep -q "api/v1/tasks" && echo "✅ tasks 路由" || echo "❌ 缺失 tasks 路由"
strings computerhub | grep -q "api/v1/nodes" && echo "✅ nodes 路由" || echo "❌ 缺失 nodes 路由"
strings computerhub | grep -q "api/v1/agent" && echo "✅ agent 路由" || echo "❌ 缺失 agent 路由"
```

---

## 4. 🚀 部署流程

```
Step 1: 备份当前 binary
  cp /home/computehub/computehub /home/computehub/computehub.bak

Step 2: 替换新 binary
  cp deploy/linux-amd64/computehub /home/computehub/computehub

Step 3: 启动新 binary
  # 启动 gateway 和 worker

Step 4: 运行路由完整性测试
  ./gatecheck.sh http://36.250.122.43:8282

Step 5: 验证集群状态
  - workers 注册正常（至少 1 个 online）
  - TUI 能正常连接
  - 可以提交任务
```

---

## 5. 🔙 回滚流程

**当路由测试失败或集群异常时：**

```bash
# 1. 停止新 binary
kill <新 gateway PID>

# 2. 恢复旧 binary
cp /home/computehub/computehub.bak /home/computehub/computehub

# 3. 重新启动
# 启动 gateway + worker

# 4. 验证恢复
./gatecheck.sh http://36.250.122.43:8282
```

**时间目标**: 完整回滚 ≤ 30 秒

---

## 6. ⚠️ 危险信号（遇到立刻停止）

| 信号 | 含义 | 行动 |
|------|------|------|
| Binary 大小 < 10MB | 可能缺失模块 | 检查 build tags，重新编译 |
| `strings` 找不到关键路由 | 子系统未嵌入 | 回退，检查编译配置 |
| 任一路由返回 404 | 路由缺失 | 回退，检查代码结构 |
| 节点注册 0 个 | Gateway-worker 连接断 | 回退，检查端口/TLS |
| Gallery 正常但其他崩 | 经典 Gallery-only 模式 | 立即回退 |

---

## 7. 📦 deploy/ 目录管理

```bash
deploy/
├── linux-amd64/
│   └── computerhub          # ✅ 当前生产版本（始终保持完整 binary）
├── windows-amd64/
│   └── computerhub.exe
├── version.txt              # 当前版本号
└── sha256sums-*.txt         # 校验和
```

**规则**:
- `deploy/linux-amd64/computehub` 始终是 **最近一次经过验证的完整 binary**
- 不要用 Gallery-only 或其他子集 binary 覆盖它
- 编译测试 binary 时放到临时目录，不要污染 `deploy/`

---

## 8. 📝 事故复盘模板

```markdown
## 部署事故复盘

**日期**: 
**版本**: 
**binary 大小**: 
**影响时间**: 
**影响范围**: 
**根因**: 
**已恢复**: Y/N
**恢复耗时**: 
**经验教训**: 
```

---

*本标准由 v1.3.15 Gallery-Only 事故经验提炼而成 (2026-06-05)*
*每次部署前必须走完 Section 2-4 的完整流程*
