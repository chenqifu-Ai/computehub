# 智能体架构设计

## 概述

设计5个专用智能体，各司其职，协同工作。

---

## 1. 侦察智能体 (Scout)

**职责**：网络侦察、端口扫描、服务识别

**能力**：
- 端口扫描（TCP/UDP）
- 服务指纹识别
- 漏洞探测
- 网段发现
- ARP 扫描

**接口**：
```
scan(target, ports) → {open_ports, services, os_info}
discover_network() → {hosts, topology}
vuln_check(target) → {vulnerabilities, risk_level}
```

**实现**：
- Python + socket
- 自定义端口扫描器
- 服务 Banner 抓取

---

## 2. 分析智能体 (Analyst)

**职责**：数据分析、报告生成、知识学习

**能力**：
- 安全报告生成
- 漏洞分析
- 风险评估
- 知识库管理
- 趋势分析

**接口**：
```
analyze(data) → {insights, recommendations}
report(target, findings) → markdown_report
learn(topic) → {knowledge, sources}
```

**实现**：
- 数据聚合
- 模板生成
- Web 搜索学习

---

## 3. 监控智能体 (Watchdog)

**职责**：持续监控、异常检测、定时汇报

**能力**：
- 端口变化监控
- 服务状态检测
- 新服务发现
- 异常告警
- 定时汇报

**接口**：
```
watch(target, interval) → {changes, alerts}
check_status(target) → {status, uptime}
report() → {summary, changes}
```

**实现**：
- Cron 定时任务
- 状态对比
- 变化检测

---

## 4. AI 智能体 (Cortex)

**职责**：调用 Ollama API、文本生成、模型管理

**能力**：
- 文本生成
- 代码生成
- 模型调用
- Embedding 处理
- 多模型协调

**接口**：
```
generate(prompt, model) → {text, tokens}
chat(messages, model) → {response, context}
list_models() → {models, sizes}
load_model(model) → {status}
```

**实现**：
- Ollama API 客户端
- http://192.168.2.134:11434
- 模型：gemma3:1b, qwen3:4b, deepseek-r1:8b

---

## 5. 协调智能体 (Coordinator)

**职责**：任务分配、资源调度、决策制定

**能力**：
- 任务分发
- 智能体协调
- 优先级管理
- 结果整合
- 决策支持

**接口**：
```
dispatch(task) → {agent, params}
collect_results(task_id) → {results, summary}
decide(context, options) → {decision, reason}
```

**实现**：
- 任务队列
- 智能体注册表
- 结果聚合

---

## 协作流程

```
用户请求
    ↓
协调智能体 (分析任务)
    ↓
    ├──→ 侦察智能体 (扫描目标)
    ├──→ 监控智能体 (持续监控)
    ├──→ AI 智能体 (AI 处理)
    └──→ 分析智能体 (生成报告)
    ↓
协调智能体 (整合结果)
    ↓
返回用户
```

---

## 示例场景

### 场景1：安全评估

1. 用户："评估 192.168.2.134 安全性"
2. 协调智能体 分配任务
3. 侦察智能体 扫描端口、识别服务
4. 分析智能体 评估风险、生成报告
5. 返回结果

### 场景2：持续监控

1. 用户："监控目标，每5分钟汇报"
2. 协调智能体 启动监控智能体
3. 监控智能体 定时检查、汇报变化
4. 发现异常 → 通知用户

### 场景3：AI 辅助分析

1. 用户："分析这些日志"
2. 协调智能体 分配给 AI 智能体
3. AI 智能体 调用 Ollama 模型
4. 分析智能体 整理结果
5. 返回分析报告

---

## 实现优先级

1. **监控智能体** - 已实现 (cron 定时汇报)
2. **侦察智能体** - 部分实现 (端口扫描)
3. **AI 智能体** - 发现入口 (Ollama API)
4. **分析智能体** - 待实现
5. **协调智能体** - 待实现