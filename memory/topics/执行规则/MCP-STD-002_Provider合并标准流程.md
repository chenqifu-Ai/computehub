# OpenClaw 模型配置合并标准流程 (MCP-STD-002)

> **制定日期**: 2026-05-23 | **最后修改**: 2026-05-23  
> **适用范围**: OpenClaw 模型 provider 合并/整合/统一 API 端点  
> **版本**: v1.0  
> **前置标准**: [MCP-STD-001](模型配置修改标准流程.md)

---

## 🎯 合并场景

以下情况适用此标准：

| 场景 | 示例 | 说明 |
|------|------|------|
| 同一 API 端点多 provider | `zhangtuo-ai` 和 `zhangtuo-ai-common` 指向同一个端点 | 统一为单 provider |
| 旧 provider 迁移 | 从 `old-provider` 迁移到 `new-provider` | 别名映射同步更新 |
| API Key 轮换 | 所有 provider 统一更新为新 key | 避免多 key 管理混乱 |
| 模型整合 | 多个 provider 的不同模型归并 | 减少 provider 数量 |

---

## 一、核心原则

1. **合并后保留单 provider**，目标 provider 名可自定义（通常保留名称更短的）
2. **合并后保留目标 provider 的原有模型** + 被合并 provider 的所有模型
3. **别名映射必须 100% 迁移**，不允许有任何别名丢失
4. **合并前必须备份**，合并后必须验证
5. **不改动其他无关 provider**

---

## 二、完整操作流程（7 步）

### 第 0 步：读取当前配置并确认

```bash
python3 -c "
import json
CONFIG = '/root/.openclaw/workspace/openclaw.json'
with open(CONFIG) as f:
    config = json.load(f)
providers = config['models']['providers']

print('=== 当前 Provider 列表 ===')
for name, prov in providers.items():
    print(f'{name}: {prov.get(\"baseUrl\", \"N/A\")} -> {len(prov.get(\"models\", []))} models')

print()
print('=== 别名映射 ===')
for path, info in config['agents']['defaults']['models'].items():
    if 'alias' in info:
        print(f'  [{info[\"alias\"]}] -> {path}')

print()
print(f'=== Primary: {config[\"agents\"][\"defaults\"][\"model\"][\"primary\"]} ===')
"
```

**确认要点：**
- [ ] 目标 provider 存在
- [ ] 被合并 provider 存在
- [ ] 两个 provider 的 baseUrl 是否一致（通常一致）
- [ ] 检查是否有别名指向被合并 provider（必须全部迁移）

### 第 1 步：备份配置

```bash
cp /root/.openclaw/workspace/openclaw.json \
   /root/.openclaw/workspace/openclaw.json.bak.$(date +%Y%m%d%H%M%S)
echo "✅ 备份完成"
```

### 第 2 步：合并 provider 配置

```python
import json

CONFIG = '/root/.openclaw/workspace/openclaw.json'
with open(CONFIG) as f:
    config = json.load(f)

providers = config['models']['providers']

# === 选择目标 provider 和被合并 provider ===
TARGET = 'zhangtuo-ai'        # 目标（保留）
SOURCE = 'zhangtuo-ai-common'  # 被合并（删除）

# 1. 用 SOURCE 的 API Key 覆盖 TARGET
providers[TARGET]['apiKey'] = providers[SOURCE]['apiKey']
print(f"✅ 合并 API Key: {SOURCE} -> {TARGET}")

# 2. 将 SOURCE 的所有模型加入 TARGET（去重）
source_models = {m['id']: m for m in providers[TARGET]['models']}
for model in providers[SOURCE]['models']:
    if model['id'] not in source_models:
        providers[TARGET]['models'].append(model)
        source_models[model['id']] = model
        print(f"  添加模型: {model['id']}")
    else:
        print(f"  已存在: {model['id']}")

print(f"✅ {TARGET} 现有 {len(providers[TARGET]['models'])} 个模型")
```

### 第 3 步：迁移别名映射

```python
agent_models = config['agents']['defaults']['models']

# 找到所有指向 SOURCE 的别名，迁移到 TARGET
aliases_to_delete = []
for full_path, info in list(agent_models.items()):
    if full_path.startswith(f'{SOURCE}/'):
        new_path = full_path.replace(f'{SOURCE}/', f'{TARGET}/')
        agent_models[new_path] = info
        aliases_to_delete.append(full_path)
        print(f"  迁移别名: {full_path} → {new_path}")

# 删除旧映射
for old_path in aliases_to_delete:
    if old_path in agent_models:
        del agent_models[old_path]

print(f"✅ 迁移 {len(aliases_to_delete)} 个别名映射")
```

### 第 4 步：删除被合并 provider

```python
del providers[SOURCE]
print(f"✅ 已删除 provider: {SOURCE}")
```

### 第 5 步：保存配置

```python
with open(CONFIG, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
print("✅ 配置已保存")
```

### 第 6 步：验证链路（必须执行！）

```bash
python3 -c "
import json

CONFIG = '/root/.openclaw/workspace/openclaw.json'
with open(CONFIG) as f:
    config = json.load(f)

providers = config['models']['providers']
agent_models = config['agents']['defaults']['models']
all_ok = True

# 验证所有别名
print('=== 别名链路验证 ===')
for full_path, info in agent_models.items():
    if 'alias' not in info:
        continue
    alias = info['alias']
    provider_name = full_path.split('/')[0]
    model_id = full_path.split('/')[1]
    
    if provider_name not in providers:
        print(f'  ❌ {alias}: provider \"{provider_name}\" NOT FOUND!')
        all_ok = False
    else:
        provider = providers[provider_name]
        model_found = any(m['id'] == model_id for m in provider['models'])
        if model_found:
            reasoning = next((m.get('reasoning', False) for m in provider['models'] if m['id'] == model_id), False)
            print(f'  ✅ {alias} -> {full_path} (reasoning={reasoning})')
        else:
            print(f'  ❌ {alias}: model \"{model_id}\" NOT in provider \"{provider_name}\"!')
            all_ok = False

# 验证 primary
print()
print('=== Primary 验证 ===')
primary = config['agents']['defaults']['model']['primary']
prov, model = primary.split('/')
if prov in providers and any(m['id'] == model for m in providers[prov]['models']):
    print(f'  ✅ primary: {primary}')
else:
    print(f'  ❌ primary: {primary} NOT VALID!')
    all_ok = False

# 验证被合并 provider 已被删除
print()
print('=== 被合并 provider 验证 ===')
if 'zhangtuo-ai-common' in providers:
    print('  ❌ 被合并 provider 仍存在！')
    all_ok = False
else:
    print('  ✅ 被合并 provider 已删除')

if all_ok:
    print()
    print('✅ 所有链路验证通过！')
else:
    print()
    print('❌ 存在错误链路，请修正！')
    exit(1)
"
```

### 第 7 步：重启 Gateway

```bash
openclaw gateway restart
sleep 3
openclaw gateway status
```

---

## 三、合并后配置示例

### 合并前

```json
{
  "providers": {
    "zhangtuo-ai": {
      "baseUrl": "https://ai.zhangtuokeji.top:9090/v1",
      "apiKey": "sk-旧key...",
      "models": ["deepseek-v3.1:671b", "deepseek-v4-flash", ...]
    },
    "zhangtuo-ai-common": {
      "baseUrl": "https://ai.zhangtuokeji.top:9090/v1",
      "apiKey": "sk-NewAPIkey...",
      "models": ["qwen3.6-35b-common"]
    }
  },
  "agents": {
    "defaults": {
      "models": {
        "zhangtuo-ai/deepseek-v4-flash": { "alias": "ds-v4-flash" },
        "zhangtuo-ai-common/qwen3.6-35b-common": { "alias": "zhangtuo-common" }
      }
    }
  }
}
```

### 合并后

```json
{
  "providers": {
    "zhangtuo-ai": {
      "baseUrl": "https://ai.zhangtuokeji.top:9090/v1",
      "apiKey": "sk-NewAPIkey...",  // 更新为新 key
      "models": ["deepseek-v3.1:671b", "deepseek-v4-flash", ..., "qwen3.6-35b-common"]  // 合并所有模型
    }
    // zhangtuo-ai-common 已删除
  },
  "agents": {
    "defaults": {
      "models": {
        "zhangtuo-ai/deepseek-v4-flash": { "alias": "ds-v4-flash" },
        "zhangtuo-ai/qwen3.6-35b-common": { "alias": "zhangtuo-common" }  // 路径已更新
      }
    }
  }
}
```

---

## 四、常见错误模式

### ❌ 错误 1：别名迁移不完整

只更新部分别名，遗漏其他指向被合并 provider 的别名。

**检查方法：** 合并前先用脚本统计所有指向被合并 provider 的别名数量。

### ❌ 错误 2：模型重复

被合并 provider 的模型已存在于目标 provider 中，直接追加导致重复。

**解决：** 用 `set` 或字典去重。

### ❌ 错误 3：API Key 未统一

合并后目标 provider 仍使用旧 key，被合并 provider 使用新 key。

**解决：** 合并时明确选择用谁的 key，通常用被合并 provider 的 key（因为可能是新的）。

### ❌ 错误 4：忽略 primary 验证

合并后 primary 指向的 provider 已被删除。

**解决：** 合并前检查 primary 指向的 provider 是否是要被合并的。

---

## 五、合并前后检查清单

### 合并前

- [ ] 确认目标 provider 存在
- [ ] 确认被合并 provider 存在
- [ ] 统计所有指向被合并 provider 的别名
- [ ] 确认 primary 不指向被合并 provider
- [ ] 备份配置

### 合并后

- [ ] 所有别名链路验证通过（无 ❌）
- [ ] primary 验证通过
- [ ] 被合并 provider 已删除
- [ ] 目标 provider 包含所有合并前的模型
- [ ] API Key 已统一
- [ ] Gateway 已重启
- [ ] 测试主要模型可正常调用

---

## 六、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-05-23 | v1.0 | 初次制定：`zhangtuo-ai-common` → `zhangtuo-ai` 合并 |

---

*本文档由小智根据实际合并操作生成，后续合并操作按此标准执行。*
