# ECS OpenClaw 本地模型代理配置修复

**日期**: 2026-06-27  
**负责人**: 端智  
**操作类型**: 配置修复 + 新增

---

## 问题描述

ECS (36.250.122.43) 上 OpenClaw 配置的 primary model 指向了不存在的 provider/model 组合：

- **旧配置**: `zhangtuo-ai-main/deepseek-v3.1:671b`
- **问题**: `zhangtuo-ai-main` 这个 provider 下没有定义 `deepseek-v3.1:671b` 模型，只有 `qwen3.6-35b`、`qwen3.6-35b-common`、`deepseek-v4-flash`
- **影响**: main agent 无法启动/无法推理

---

## 修复方案

### 1. 修正 Primary Model

```
旧: zhangtuo-ai-main/deepseek-v3.1:671b
新: zhangtuo-ai-main/qwen3.6-35b
```

同时在 agents.list 中修正 main agent 的 model 字段。

### 2. 新增 proxy-local Provider

本机已有 vLLM 代理跑在 `http://127.0.0.1:8765/v1`，ECS 上也部署了同样的 proxy，因此将配置同步到 ECS：

```json
{
  "proxy-local": {
    "baseUrl": "http://127.0.0.1:8765/v1",
    "apiKey": "",
    "api": "openai-completions",
    "models": [{
      "id": "qwen3.6-35b",
      "name": "Qwen 3.6-35B (Local Proxy)",
      "reasoning": true,
      "contextWindow": 262144,
      "maxTokens": 4096
    }]
  }
}
```

### 3. 新增 Alias

```
proxy-local/qwen3.6-35b → zhangtuo-proxy
```

---

## 配置前后对比

| 项目 | 旧配置 | 新配置 |
|------|--------|--------|
| Primary | zhangtuo-ai-main/deepseek-v3.1:671b ❌ | zhangtuo-ai-main/qwen3.6-35b ✅ |
| Main Agent | zhangtuo-ai-main/deepseek-v3.1:671b ❌ | zhangtuo-ai-main/qwen3.6-35b ✅ |
| proxy-local Provider | 不存在 | ✅ 已添加 |
| zhangtuo-proxy Alias | 不存在 | ✅ 已添加 |

---

## 配置文件

- **ECS 配置路径**: `/home/computehub/.openclaw/openclaw.json`
- **备份**: `openclaw.json.bak.20260627`
- **Gateway 重启**: `openclaw gateway restart` ✅

---

## 验证结果

- ✅ proxy-local 服务在线：`curl http://127.0.0.1:8765/v1/models` 返回正常
- ✅ 测试 chat 请求：返回正常推理结果
- ✅ Gateway 重启后端口 18789 正常监听
- ✅ 配置中 providers 包含 proxy-local

---

## 注意事项

1. `proxy-local` 的 baseUrl 是 `127.0.0.1:8765`，仅在 ECS 本机上可用
2. 如果 ECS 上 proxy 服务挂了，`zhangtuo-proxy` alias 会调用失败
3. 其他节点（Windows/Android）无法通过 127.0.0.1 访问此 proxy
4. 主 agent 使用的 `zhangtuo-ai-main` 需要通过 `zhangtuokeji.top:9090` 外网 API

---

## 相关文件

- ECS OpenClaw 配置: `/home/computehub/.openclaw/openclaw.json`
- 本地 OpenClaw 配置: `/root/.openclaw/openclaw.json`
- Gallery 共享目录: `http://36.250.122.43:8282/gallery`
