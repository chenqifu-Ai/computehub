# STD-002: Gateway 任务调度 node 字段兼容

**制定日期**: 2026-05-19  
**类型**: 任务调度 / 兼容性  
**状态**: ✅ 已实施

---

## 📌 核心问题

Gateway 的 `TaskSubmit` struct 原本只有 `node_id` 和 `assigned_node` 两个字段，没有 `node` 字段。

当客户端提交任务时使用 `"node"` 键（如 `{"command": "echo test", "node": "Windows-mobile-01"}`），Go JSON 解析会**静默忽略**该字段，导致 `AssignedNode` 为空 → 任务走自动调度而非定向调度到指定节点。

**Bug 表现**: 明明指定了目标节点，任务却分配给了其他节点。

## 🔧 修复方案

在 `TaskSubmit` struct 中添加 `node` 字段兼容，并统一映射到 `AssignedNode`。

### 修改位置
Gateway `TaskSubmit` struct（Go 代码）

### 新增字段
```go
Node         string `json:"node,omitempty"`   // 兼容旧版客户端
NodeID       string `json:"node_id"`
AssignedNode string `json:"assigned_node"`
```

### 映射逻辑
解析任务时，优先级为：`node` → `node_id` → `assigned_node`，任一有值即走定向调度：

```go
assigned := task.AssignedNode
if assigned == "" {
    assigned = task.Node
}
if assigned == "" {
    assigned = task.NodeID
}
if assigned != "" {
    task.AssignedNode = assigned
}
```

## 📝 使用说明

现在三种写法**均可用**，语义等价：

```bash
# 写法 1: node（最简，推荐）
curl -d '{"command":"task","node":"Windows-mobile-01"}'

# 写法 2: node_id（Go 原生）
curl -d '{"command":"task","node_id":"Windows-mobile-01"}'

# 写法 3: assigned_node（语义明确）
curl -d '{"command":"task","assigned_node":"Windows-mobile-01"}'
```

## ✅ 验证

已验证三种写法均能正确定向调度到指定节点。

## 🔄 后续建议

- Python 客户端建议统一使用 `node` 或 `node_id`（推荐 `node`，更简洁）
- 其他语言客户端同理，三种写法均可
- 未来如果重构，可以只保留 `node` 一个字段

---

*记录人: 小智*  
*审核: 老大*
