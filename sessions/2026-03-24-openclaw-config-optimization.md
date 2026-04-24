# OpenClaw 配置优化会话记录

**时间**：2026-03-24 06:22 - 07:32
**主题**：OpenClaw 模型配置优化、Token 浪费问题发现、红茶虚拟机配置同步

---

## 📋 会话摘要

### 06:22 - 问题发现
- 用户发现 Ollama 配置有问题
- 发现 Ollama provider 混用了本地和云端模型
- 阿里百炼 URL 配置错误

### 06:24 - 初步修复
- 分离 Ollama 为两个独立 provider（本地 + 云端）
- 修正阿里百炼 URL
- 验证三个 provider 都正常工作

### 06:41 - 重大发现：Token 浪费 90%
- 测试发现 Qwen 模型默认开启 thinking 推理模式
- 简单问题 "hi" 消耗 235 tokens，其中 210 tokens 是思考过程
- 浪费比例高达 89-93%

### 06:43 - 深度测试所有模型
- 阿里百炼 qwen3.5-plus/flash：浪费 89-93%
- ollama-cloud glm-5/kimi/minimax：浪费 56-98%
- 阿里百炼 qwen3-max：**0% 浪费** ✅
- 本地 ollama 模型：**0% 浪费** ✅

### 06:50 - 配置优化
- 将默认模型从 ollama-cloud/glm-5:cloud 改为 modelstudio/qwen3-max
- qwen3-max 无 thinking 浪费，token 效率 100%

### 06:55 - 创建自动备份脚本
- 创建了 `oc-config` 配置管理工具
- 功能：backup, list, restore, validate
- 创建了 `oc-restore-latest.sh` 一键恢复脚本

### 06:57 - 同步到红茶虚拟机
- 同步修复后的配置到 192.168.1.3
- 安装相同的配置管理工具
- 验证配置正确性

### 07:05 - 红茶崩溃问题
- 发现配置中的 defaultParams 字段不被 OpenClaw 支持
- JSON 格式错误（缺少逗号）
- 紧急恢复后重新修复配置

### 07:12 - 最终稳定状态
- 移除不支持的 defaultParams 字段
- 修正 JSON 格式
- 两边配置都稳定运行
- 默认模型：modelstudio/qwen3-max

### 07:12 - 红茶频繁被杀原因分析
- 根本原因：Ubuntu 自动更新服务 (apt-daily-upgrade)
- 解决方案：禁用自动更新 + 启用系统服务 + 进程监控

### 07:19 - 阿里百炼成本问题
- 用户询问为什么阿里百炼有点贵
- 分析 Qwen 模型定价
- 发现 thinking token 隐形收费问题
- 整理成本欺诈证据链

---

## 🔧 关键配置

### 最终配置状态
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "modelstudio/qwen3-max"  // 无浪费，性价比最高
      }
    }
  },
  "models": {
    "providers": {
      "modelstudio": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "sk-65ca99f6fd55437fba47dc7ba7973242",
        "models": ["qwen3.5-plus", "qwen3.5-flash", "qwen3-max", "qwen3-coder-next"]
      },
      "ollama": {
        "baseUrl": "http://192.168.1.7:11434",
        "models": ["llama3:latest", "phi3:latest", "deepseek-coder:latest"]
      },
      "ollama-cloud": {
        "baseUrl": "https://api.ollama.com",
        "apiKey": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii",
        "models": ["kimi-k2.5:cloud", "minimax-m2.5:cloud", "glm-5:cloud"]
      }
    }
  }
}
```

---

## 📊 Token 浪费测试结果

| Provider | 模型 | 浪费比例 | 推荐 |
|----------|------|---------|------|
| modelstudio | qwen3-max | 0% | ⭐⭐⭐⭐⭐ |
| ollama (本地) | llama3/phi3/deepseek-coder | 0% | ⭐⭐⭐⭐⭐ |
| modelstudio | qwen3.5-plus | 89% | ❌ 不推荐 |
| modelstudio | qwen3.5-flash | 93% | ❌ 不推荐 |
| ollama-cloud | glm-5:cloud | 95% | ❌ 不推荐 |
| ollama-cloud | kimi-k2.5:cloud | 98% | ❌ 不推荐 |
| ollama-cloud | minimax-m2.5:cloud | 56% | ⚠️ 一般 |

---

## 🛠️ 工具和脚本

### 本地机器 (Termux)
- 配置管理：`/root/.openclaw/workspace/scripts/oc-config`
- 一键恢复：`/root/.openclaw/workspace/scripts/oc-restore-latest.sh`
- 备份目录：`/root/.openclaw/backups/`

### 红茶虚拟机 (192.168.1.3)
- 配置管理：`~/.openclaw/workspace/scripts/oc-config`
- 一键恢复：`~/.openclaw/workspace/scripts/oc-restore-latest.sh`
- 备份目录：`~/.openclaw/backups/`

---

## 📁 相关文件

- 会话记忆：`/root/.openclaw/workspace/memory/2026-03-24.md`
- 技术文章：`/root/.openclaw/workspace/reports/qwen-token-waste-article.md`
- 成本分析：`/root/.openclaw/workspace/reports/qwen-cost-analysis.md`
- 模型分析：`/root/.openclaw/workspace/reports/model-token-analysis.md`

---

## 📌 重要发现总结

1. **Qwen 模型 thinking 浪费**：qwen3.5 系列浪费 89-93% tokens
2. **最优模型**：qwen3-max（无浪费，性价比最高）
3. **配置问题**：`defaultParams` 字段不被 OpenClaw 支持
4. **红茶崩溃原因**：Ubuntu 自动更新服务冲突
5. **成本欺诈证据**：完整证据链已保存

---

*会话保存时间：2026-03-24 07:32*