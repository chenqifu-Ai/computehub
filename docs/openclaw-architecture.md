# OpenClaw Agent & Gateway 架构

```mermaid
mindmap
  root((OpenClaw))
    入口层
      openclaw CLI
      openclaw-tui 终端界面
      WebChat / Discord / 其他Channel
    
    ::icon(fa fa-terminal)
    
    Gateway 网关层
      端口 18789
      HTTP API 服务器
        REST API 端点
        Session 管理
        Provider/Model 路由
        SSE 流式转发
      核心功能
        会话生命周期
          create / resume / close
        认证与授权
          Token / API Key
        请求路由
          Channel → Session → Agent
            WebChat → session-A
            TUI → session-B
            Discord → session-C
        消息队列
          入站队列
          出站队列
        Provider 调度
          选择Provider
          负载均衡
          Failover 降级
        Plugins 插件系统
          Feishu
          自定义扩展
    
    ::icon(fa fa-server)
    
    Agent 智能体层
      会话上下文
        System Prompt 构建
        Tools 注册管理
        Memory 加载
          每日日记 memory/YYYY-MM-DD.md
          MEMORY.md 长期记忆
          SOUL.md 人格设定
          USER.md 用户信息
          HEARTBEAT.md 心跳任务
      推理循环
        User Message
          ↓
        Context 组装
          System + Tools + History + User
          ↓
        LLM 调用
          ↓
        Response / Tool Calls
          ↓
        Tool 执行
          read / write / exec / web_search ...
          ↓
        结果回注
          ↓
        继续或结束
      Skills 技能系统
        SKILL.md 驱动
        Reference 文件
        Scripts 脚本
      Model Alias 管理
        deepseek-v4-flash → ollama-cloud
        qwen3.6-35b → vllm-local
    
    ::icon(fa fa-robot)
    
    Provider 模型层
      本地 Provider
        vllm-local
          http://172.29.174.77:8765/v1
          qwen3.6-35b
        ollama (本地)
          http://127.0.0.1:11434
          本地小模型
      远程 Provider
        qwen-custom
          http://58.23.129.98:8001/v1
          qwen3.6-35b
        gemma-custom
          http://58.23.129.98:8000/v1
          gemma-4-31b
        ollama-cloud
          https://api.ollama.com
          deepseek-v4-flash / glm-5 / kimi-k2.5 ...
        modelstudio (阿里百炼)
          https://dashscope.aliyuncs.com
          qwen3.5-plus / qwen3-max ...
        zhangtuokeji
          https://ai.zhangtuokeji.top:9090/v1
          qwen3.6-35b
    
    ::icon(fa fa-database)
```

## 数据流

```mermaid
sequenceDiagram
    participant U as 用户 (TUI/WebChat)
    participant GW as Gateway (端口18789)
    participant AG as Agent (每个Session)
    participant LLM as Provider (vLLM/Ollama)

    Note over U,LLM: 标准请求流程
    
    U->>GW: HTTP POST /chat/completions
    Note over GW: 认证+路由
    
    GW->>GW: 查找/创建 Session
    GW->>AG: 转发消息
    
    Note over AG: Context 组装
    Note over AG: SystemPrompt + Tools + History
    
    AG->>LLM: API 调用 (根据model.primary)
    LLM-->>AG: Response / Stream
    
    AG->>AG: 解析响应 / 执行Tool
    
    alt Tool Call
        AG->>GW: exec / read / web_search
        GW-->>AG: Tool结果
        AG->>LLM: 继续推理
    end
    
    AG-->>GW: 最终响应
    GW-->>U: HTTP Response / SSE Stream
```

## 进程架构

```mermaid
graph TB
    subgraph "openclaw 主进程"
        CLI["openclaw CLI"]
        TUI["openclaw-tui (终端UI)"]
    end

    subgraph "Gateway 子进程"
        GW["openclaw-gateway"]
        API["HTTP Server :18789"]
        SS["Session Store"]
    end

    subgraph "Agent 嵌入式运行时"
        AG1["Session A Agent"]
        AG2["Session B Agent"]
        AG3["Session C Agent"]
        SM["System Monitor"]
        Skills["Skills 注册表"]
    end

    subgraph "外部"
        Providers["LLM Provider<br/>vLLM / Ollama Cloud / ..."]
        Channels["信道接入<br/>WebChat / Discord / TG"]
    end

    CLI -->|spawn| GW
    TUI -->|WebSocket / HTTP| API
    Channels -->|webhook / polling| API
    
    GW -->|route| AG1
    GW -->|route| AG2
    GW -->|route| AG3
    
    AG1 -->|API call| Providers
    AG2 -->|API call| Providers
    AG3 -->|API call| Providers
    
    AG1 -.->|load| SS
    AG2 -.->|load| SS
    AG3 -.->|load| SS
    
    SM -->|monitor| GW
    Skills -->|tool definitions| AG1
    Skills -->|tool definitions| AG2
```

## 关键概念

| 概念 | 说明 |
|------|------|
| **Gateway** | 无状态 HTTP 网关，负责认证、路由、Session 生命周期管理 |
| **Agent** | 有状态的智能体运行时，负责对话上下文、Tool 执行、LLM 调用 |
| **Session** | 一个对话实例，包含完整历史。每个 Session 有一个 Agent |
| **Provider** | LLM 服务提供方，可以本地或远程 |
| **Channel** | 外部接入方式（WebChat、Discord、Telegram） |
| **Plugin** | 扩展功能，如飞书集成 |
| **Skill** | Agent 的能力包，含 SKILL.md + scripts + references |
