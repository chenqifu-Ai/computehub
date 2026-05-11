# 📝 API 变更日志

## 版本管理原则

### 版本号规范
- **主版本 (v1)**: 不兼容的API变更
- **次版本 (v2)**: 向后兼容的功能性新增
- **修订版本 (v1.1)**: 向后兼容的问题修正

### 兼容性承诺
- 主版本变更必须提供迁移指南
- 次版本变更必须保持向后兼容
- 废弃的API必须提供替代方案和过渡期

## 变更记录

### 2026-05-08 - 事故复盘与预防
**变更类型**: 流程改进
**影响范围**: 所有API端点
**变更内容**:
- 建立API监控和告警系统
- 制定更新检查清单
- 完善变更日志记录规范

### 2026-05-07 - Walker调度器更新
**变更类型**: 功能优化
**影响范围**: 任务调度相关API
**变更内容**:
- 修复调度双调用bug
- 优化任务提交性能
- 调整API端点路径

#### API端点变化
| 功能 | 旧端点 | 新端点 | 状态 |
|------|--------|--------|------|
| 任务提交 | `/api/v1/tasks` | `/api/v1/tasks/submit` | ✅ 已更新 |
| 任务结果 | `/api/v1/tasks` | `/api/v1/tasks/result` | ✅ 已更新 |
| 节点注册 | 无变化 | 无变化 | ✅ 兼容 |
| 健康检查 | 无变化 | 无变化 | ✅ 兼容 |

#### 参数格式要求
```json
// 任务提交请求格式
{
  "task_id": "string",      // 任务ID
  "command": "string",     // 执行命令
  "timeout": number,       // 超时时间(秒)
  "node_id": "string"      // 目标节点ID
}

// 任务结果查询格式  
{
  "task_id": "string",      // 任务ID
  "node_id": "string"      // 节点ID
}
```

### 2026-04-20 - 初始版本
**变更类型**: 初始发布
**影响范围**: 所有功能
**变更内容**:
- ComputeHub v1.0 初始API设计
- 基础节点管理功能
- 任务调度执行功能

## 📊 当前支持的API端点

### v1 API (稳定版本)
```
GET    /api/v1/nodes/list          # 节点列表
POST   /api/v1/nodes/register     # 节点注册  
POST   /api/v1/nodes/unregister   # 节点注销
POST   /api/v1/nodes/heartbeat    # 节点心跳
POST   /api/v1/tasks/submit       # 任务提交
POST   /api/v1/tasks/result       # 任务结果
```

### v2 API (监控功能)
```
GET    /api/v2/health             # 健康检查
GET    /api/v2/nodes             # 节点详细信息
GET    /api/v2/map/global        # 全局地图数据
GET    /api/v2/gpu/realtime      # GPU实时监控
```

## 🚨 废弃API列表

### 已废弃的端点
| 端点 | 废弃时间 | 替代方案 | 完全移除时间 |
|------|----------|----------|--------------|
| `/api/v1/tasks` | 2026-05-07 | `/api/v1/tasks/submit` | 2026-06-07 |

## 🔧 故障处理指南

### 常见错误代码
- `404 Not Found`: API端点不存在
- `400 Bad Request`: 参数格式错误
- `500 Internal Error`: 服务器内部错误
- `503 Service Unavailable`: 服务不可用

### 故障排查步骤
1. 检查API端点路径是否正确
2. 验证请求参数格式
3. 查看服务日志输出
4. 检查网络连通性
5. 验证节点状态

---
*最后更新: 2026-05-08*
*维护团队: ComputeHub 开发组*