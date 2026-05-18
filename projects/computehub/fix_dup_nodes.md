# 节点去重 Bug 分析

## Bug 1: Visualizer 节点跨区域重复

**文件**: `src/visualizer/aggregator.go`
**函数**: `RegisterNodeFromKernel`

**问题**: 查重 `for i, existing := range rd.Nodes` 只在本 region 内查找。如果节点区域变化（如 `"" → "cn-east"`），旧区域的条目不会被清理，导致同一个 nodeID 出现在两个 region 下。

**修复**: 查重前先扫描所有 region，找到旧条目先删除再添加。

## Bug 2: SyncFromKernel 不清理过期节点

**文件**: `src/visualizer/bridge.go`
**函数**: `SyncFromKernel`

**问题**: 只做 add/update，不做 remove。kernel 中删除节点后，visualizer 的旧条目永远残留。

**修复**: Sync 时先清理不在 kernel 中的 visualizer 条目。

## Bug 3: Kernel RegisterNode 不支持更新

**文件**: `src/kernel/actions.go`
**函数**: `RegisterNode`

**问题**: 重复注册直接返回 error，导致 region 等信息更新不了。

**修复**: 改为 upsert 语义，更新已有节点的 Register 信息。
