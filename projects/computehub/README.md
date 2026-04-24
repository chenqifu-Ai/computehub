# ComputeHub - 确定性算力调度平台

**项目状态**: 🟡 Phase 1 整合中  
**创建日期**: 2026-04-22  
**负责人**: 小智  
**核心目标**: 基于确定性内核的海外算力调度平台

## 🚀 核心理念

**物理交付 ≫ 认知描述**

ComputeHub 是一个**物理确定性操作系统**，提供确定性的算力任务调度和系统状态管理。

## 📦 系统架构

```
Client → Gateway API → Pure Pipeline(4 级过滤) → Gene Store → Kernel → Executor → 算力节点
```

### 核心组件

| 组件 | 路径 | 功能 |
|------|------|------|
| **Gateway** | `src/gateway/gateway.go` | REST API 接口 (端口 8282) |
| **Kernel** | `src/kernel/kernel.go` | 确定性命令调度器 (单队列无竞态) |
| **Executor** | `src/executor/executor.go` | 命令执行 + 验证循环 |
| **Pure Pipeline** | `src/pure/pipeline.go` | 4 级输入过滤 (语法/语义/边界/上下文) |
| **Gene Store** | `src/gene/store.go` | 学习进化存储 (出错→修复→永久记忆) |

## 🛠️ 快速开始

### 前置条件
- Go 1.24+
- Linux/Windows/macOS

### 编译和运行

```bash
cd /root/.openclaw/workspace/projects/computehub

# 编译网关
go build -o opc-gateway main_gateway.go

# 编译 TUI
go build -o opc-tui tui.go

# 启动网关
./opc-gateway

# 启动 TUI (另一个终端)
./opc-tui
```

### API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/status` | GET | 系统状态 |
| `/api/dispatch` | POST | 命令分发 |

#### 示例

```bash
# 健康检查
curl http://localhost:8282/api/health

# 系统状态
curl http://localhost:8282/api/status

# 命令分发
curl -X POST http://localhost:8282/api/dispatch \
  -H "Content-Type: application/json" \
  -d '{"id":"test-001","command":"PING"}'
```

## ⚙️ 配置说明

配置文件：`config.json`

```json
{
  "gateway": {
    "port": 8282,
    "max_connections": 100
  },
  "kernel": {
    "buffer_size": 100,
    "max_states": 1000
  },
  "executor": {
    "sandbox_path": "/tmp/opc-sandbox"
  },
  "gene_store": {
    "path": "./genes.json"
  }
}
```

## 📊 开发进度

### Phase 1: 基础设施整合 (进行中)
- [x] 删除重复代码 (src/core/)
- [x] 修复硬编码路径
- [x] 创建 SOUL.md
- [x] 完善 .gitignore
- [ ] 更新 README.md
- [ ] 编译验证

### Phase 2: 内核扩展 (计划中)
- [ ] 增加算力相关 Action (NODE_REGISTER, GPU_MONITOR, TASK_SUBMIT 等)
- [ ] 状态持久化到数据库
- [ ] 优先级队列

### Phase 3: 节点管理 (计划中)
- [ ] 节点注册与发现
- [ ] GPU 真实监控
- [ ] 物理心跳系统
- [ ] 区域熔断机制

### Phase 4: 调度计费 (计划中)
- [ ] 智能调度器
- [ ] 真实计量计费
- [ ] 任务双校验
- [ ] 交付凭证

## 📁 项目结构

```
computehub/
├── README.md          ← 本文件
├── SOUL.md            ← 工程哲学
├── config.json        ← 配置文件
├── genes.json         ← 基因存储
├── main_gateway.go    ← 网关主入口
├── tui.go             ← TUI 主入口
├── go.mod             ← Go 模块定义
├── src/
│   ├── gateway/       ← REST API 网关
│   ├── kernel/        ← 确定性内核
│   ├── executor/      ← 执行器
│   ├── pure/          ← 净化管线
│   └── gene/          ← 基因存储
├── docs/              ← 文档
├── deploy/            ← 部署包
└── results/           ← 运行结果
```

## 🎯 工程哲学

详见 [SOUL.md](SOUL.md)

### 核心原则
1. **绝对确定性** - 消除竞态，状态可回溯
2. **防御性鲁棒性** - 默认不可信，内置自救
3. **物理真实优先** - 拒绝 Mock，真实硬件数据
4. **多级纯化** - 4 层输入过滤
5. **进化架构** - 错误→基因→永久修复

## 🔧 管理脚本

```bash
# 网关管理
./start-gateway.sh start|stop|restart|status|logs

# TUI 管理
./start-tui.sh start|stop|restart|status|logs
```

## 📝 开发规范

1. 所有代码和文档放在对应子目录
2. 每次开发完成后 `git add . && git commit`
3. 重大功能使用语义化版本号
4. 敏感配置不提交 (授权码、密钥等)

## 📈 下一步

1. **编译验证** - 确保 gateway 和 tui 都能正常编译运行
2. **内核扩展** - 增加算力调度相关 Action
3. **节点管理** - 实现 GPU 监控和节点发现
4. **前端仪表板** - 全球算力分布可视化

---

*最后更新: 2026-04-24*  
*版本: v0.2 Alpha (Phase 1 整合中)*
