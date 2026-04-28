# AI 服务器算力测试工具包

## 📋 项目概述

标准化 AI 服务器算力接入测试 SOP，支持自动化测试、报告生成、Git 版本管理。

## 🚀 快速开始

```bash
# 初始化
git init ai-benchmark
cd ai-benchmark

# 运行测试
python3 run_tests.py --targets 8000,8001,8765 --mode full

# 生成报告
python3 generate_report.py --format html --output report_20260426.html
```

## 📁 项目结构

```
ai-benchmark/
├── README.md                 # 项目说明
├── config/
│   ├── api_keys.json         # API Key 配置
│   ├── servers.yaml          # 服务器配置
│   └── email.conf            # 邮件配置
├── tests/
│   ├── p0_connectivity.py    # P0 连通性测试
│   ├── p1_performance.py     # P1 性能对比测试
│   ├── p2_stress.py          # P2 压力测试
│   ├── p3_proxy.py           # P3 代理专项
│   ├── p4_edge.py            # P4 边缘场景
│   └── utils.py              # 公共工具
├── reports/                  # 测试报告输出
├── requirements.txt
└── run_tests.py              # 主入口
```

## ⚙️ 配置说明

### 服务器配置 (config/servers.yaml)

```yaml
servers:
  local:
    url: "http://58.23.129.98:8000/v1"
    api_key: "sk-78sadn09bjawde123e"
    port: 8000
    cards: 4
  
  production:
    url: "http://58.23.129.98:8001/v1"
    api_key: "sk-78sadn09bjawde123e"
    port: 8001
    cards: 4

  proxy:
    url: "http://172.29.174.77:8765/v1"
    api_key: null
    port: 8765
    cards: 4
    type: proxy
```

### 邮件配置 (config/email.conf)

```ini
[email]
username = 19525456@qq.com
password = bzgwylbbrocdbiie
smtp_server = smtp.qq.com
smtp_port = 465
```

## 📊 测试标准

| 优先级 | 内容 | 耗时 | 通过标准 |
|--------|------|------|----------|
| P0 | 连通性 | 30min | 5/6 通过 |
| P1 | 性能对比 | 2h | 延迟<500ms, 吞吐>20 req/s |
| P2 | 压力测试 | 3h | 成功率>95%, 无OOM |
| P3 | 代理专项 | 1h | 延迟增加<50ms |
| P4 | 边缘场景 | 1h | 错误处理正确 |
