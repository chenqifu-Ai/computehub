# OPC — Open Compute Platform

分布式计算平台，内置 AI Agent。让一群机器变成一个团队，用自然语言指挥它们干活。

## 一句话

**Gateway（大脑）+ Worker（手脚）+ Agent（智商）**

## 架构图

```
                        ┌─────────────────────────────┐
                        │         Gateway              │
                        │  HTTP API · 调度 · 认证       │
                        │  Gallery · 升级 · 监控        │
                        └──────┬──────────┬────────────┘
                               │          │
              ┌────────────────┼──────────┼────────────────┐
              │                │          │                │
        ┌─────┴──────┐  ┌─────┴────┐  ┌──┴───────┐  ┌────┴─────┐
        │ Worker A   │  │ Worker B │  │ Worker C │  │  ...     │
        │ Linux ECS  │  │ Windows  │  │ Android  │  │          │
        │ ┌────────┐ │  │ ┌──────┐ │  │ ┌──────┐ │  │          │
        │ │ Agent  │ │  │ │Agent │ │  │ │Agent │ │  │          │
        │ │ └─LLM─┘│ │  │ │└─LLM┘│ │  │ │└─LLM┘│ │  │          │
        │ │ └─工具─┘│ │  │ │└工具─┘│ │  │ │└工具─┘│ │  │          │
        │ └────────┘ │  │ └──────┘ │  │ └──────┘ │  │          │
        └────────────┘  └──────────┘  └──────────┘  └──────────┘
```

## 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 内置 AI Agent | 自然语言指令 → 自动规划 → 执行工具 → 返回结果 |
| 🧠 Git 记忆系统 | Agent 记住历史操作，跨会话持续学习 |
| ⚡ 智能调度 | 任务队列 + 区域熔断 + 多种负载均衡策略 |
| 🔄 零断联升级 | test-register 子进程验证 → 无缝替换 binary |
| 🛡️ 安全纵深 | SSH 自连接拦截 / SafeCommand / Sentinel 审批 |
| 📊 实时监控 | TUI 终端面板 + Prometheus 指标 |
| 🎬 视频管线 | 文档 → TTS + 画面 → 成品视频 |
| 🖼️ Gallery | 文件管理 + AI 对话的 Web 界面 |

## 快速开始

### 1. 编译

```bash
go build -o computehub ./cmd/computehub/
```

### 2. 启动 Gateway

```bash
./computehub gateway --port 8282
```

### 3. 启动 Worker

```bash
./computehub worker --gw http://localhost:8282 --node-id my-node
```

### 4. 使用 TUI 监控

```bash
./computehub tui --gw http://localhost:8282
```

## 项目结构

```
OPC/
├── cmd/              # 入口
│   ├── computehub/   # 一体化 CLI
│   ├── gateway/      # 独立 Gateway
│   ├── node/         # 独立 Worker
│   └── tui/          # 终端 UI
├── src/              # 核心源码
│   ├── gateway/      # Gateway 核心（HTTP API + 调度）
│   ├── workercmd/    # Worker 全套（注册/心跳/升级/Agent）
│   ├── agent/        # AI Agent（LLM + 工具 + 记忆）
│   ├── scheduler/    # 任务调度（队列/熔断/负载均衡）
│   ├── kernel/       # 内核（节点管理 + 动作分发）
│   ├── composer/     # LLM 客户端（多 Provider 适配）
│   ├── monitor/      # 健康监控
│   ├── pure/         # 输入过滤管线
│   └── ...
├── deploy/           # 编译产物 + 版本
├── scripts/          # 构建/部署/运维脚本
└── docs/             # 设计文档
```

## 编译目标

| 平台 | 架构 | 命令 |
|------|------|------|
| Linux | amd64 | `GOOS=linux GOARCH=amd64 go build -o computehub ./cmd/computehub/` |
| Linux | arm64 | `GOOS=linux GOARCH=arm64 go build -o computehub ./cmd/computehub/` |
| macOS | amd64 | `GOOS=darwin GOARCH=amd64 go build -o computehub ./cmd/computehub/` |
| macOS | arm64 | `GOOS=darwin GOARCH=arm64 go build -o computehub ./cmd/computehub/` |
| Windows | amd64 | `GOOS=windows GOARCH=amd64 go build -o computehub.exe ./cmd/computehub/` |

## 测试

```bash
go test ./...                    # 全部
go test ./src/gateway/ -v        # Gateway API（47 个测试）
go test ./src/scheduler/ -v      # 调度器
go test ./src/agent/ -v          # AI Agent
```

## 配置

```json
// llm-config.json
{
  "default_provider": "newapi",
  "providers": {
    "newapi": {
      "api_url": "https://your-api.example.com/v1",
      "api_key": "sk-...",
      "model": "qwen3.6-35b"
    }
  }
}
```

## 版本

- **当前**: v1.3.13
- **依赖**: 仅 `golang.org/x/term` + `golang.org/x/sys`
- **代码量**: ~30K 行 Go，21 个测试文件

## License

MIT
