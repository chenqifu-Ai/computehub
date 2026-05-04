# 规范文档：图片识别 - API 远程识别方案

> **编号**: DOC-IMG-001  
> **制定日期**: 2026-04-29  
> **适用范围**: OpenClaw 工作区所有图片识别需求  
> **版本**: v1.0

---

## 一、背景

### 问题

Termux 环境下 Sharp 图像处理库因依赖缺失报错：

```
Error: libvips-42.so.42: cannot open shared object file: No such file or directory
```

**原因**：Android 系统（Termux）缺少 `libvips` 等系统级依赖，Sharp 无法正常工作。

### 替代方案

通过 **qwen3.6-35b 的 OpenAI 兼容 API** 远程传图识别，绕过本地依赖问题。

---

## 二、方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Sharp（本地）** | 速度快，无网络延迟 | 依赖 libvips，Termux 不可用 | ❌ 不适用 |
| **API 远程识别** | 无依赖，准确率高 | 需网络，响应稍慢 | ✅ **推荐** |
| **Base64 编码传图** | 简单直接 | payload 过大，耗时 | ⚠️ 备选 |

---

## 三、API 调用规范

### 3.1 端点信息

| 项目 | 值 |
|------|-----|
| **API 地址** | `http://10.111.223.227:8765/v1/chat/completions` |
| **备用地址** | `http://192.168.2.54:8765/v1/chat/completions` |
| **API Key** | `sk-78sadn09bjawde123e` |
| **模型** | `qwen3.6-35b` |
| **API 格式** | OpenAI 兼容 |

### 3.2 请求格式

```python
import base64
import urllib.request
import json

def analyze_image(image_path: str, prompt: str = "请详细分析这张图片") -> dict:
    """
    通过 API 识别图片
    
    Args:
        image_path: 图片本地路径
        prompt: 分析提示词
    
    Returns:
        包含 reasoning 和 content 的响应
    """
    # 1. 读取图片并转 Base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # 2. 构建消息
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
    }]
    
    # 3. 构建请求
    payload = json.dumps({
        "model": "qwen3.6-35b",
        "messages": messages,
        "max_tokens": 4000,
        "temperature": 0.7
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "http://10.111.223.227:8765/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-78sadn09bjawde123e"
        }
    )
    
    # 4. 发送请求
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    
    return data
```

### 3.3 响应处理

qwen3.6-35b 是 **reasoning-first 模型**，输出在 `reasoning` 字段：

```python
data = analyze_image("/path/to/image.jpg")

# 获取模型回答（优先取 reasoning，其次取 content）
msg = data.get("choices", [{}])[0].get("message", {})
reasoning = msg.get("reasoning", "") or ""
content = msg.get("content", "") or ""

final_answer = reasoning if reasoning else content
print(final_answer)
```

---

## 四、使用示例

### 4.1 基础识别

```python
result = analyze_image(
    "/data/data/com.termux/files/home/downloads/screenshot.jpg",
    "请详细分析这张图片的内容"
)
```

**输出示例**：

```markdown
这是一张手机终端截图，记录了 OpenClaw TUI 的完整对话...

## 关键信息
- 时间：05:48 ~ 11:15
- 内存：11.53GB 可用
- 模型：qwen3.6-35b
- 代理：192.168.2.54:8765
```

### 4.2 指定分析维度

```python
result = analyze_image(
    "chart.png",
    "请从以下维度分析：1) 图表类型 2) 数据趋势 3) 关键指标 4) 异常点"
)
```

### 4.3 长图处理

对于超长截图（>5000px 高度），建议分段描述：

```python
def analyze_long_image(image_path: str):
    """长图分段分析"""
    from PIL import Image
    
    img = Image.open(image_path)
    height = img.size[1]
    
    if height > 5000:
        print(f"长图 ({height}px)，建议分段识别")
        # 方案 1: 裁剪关键区域
        # 方案 2: 让模型逐段分析
    
    return analyze_image(image_path, "这是一张长截图，请从上到下分段分析")
```

---

## 五、注意事项

### 5.1 图片格式

| 格式 | 支持 | 建议 |
|------|------|------|
| JPEG | ✅ | 压缩比好，推荐 |
| PNG | ✅ | 无损，但体积大 |
| WEBP | ⚠️ | 部分模型不支持 |
| GIF | ❌ | 不支持动态图 |

### 5.2 图片大小

| 限制 | 建议 |
|------|------|
| **单图最大** | ~20MB（取决于模型限制） |
| **推荐大小** | <5MB，分辨率 <4000px |
| **超长图** | 超过 10000px 建议裁剪 |

### 5.3 性能

| 指标 | 值 |
|------|-----|
| **响应时间** | 5-60s（取决于图片复杂度） |
| **reasoning 长度** | 通常 2000-10000 字符 |
| **并发限制** | 建议串行，避免 API 限流 |

### 5.4 成本

| 项目 | 说明 |
|------|------|
| **计费方式** | 按 token 计费 |
| **图片计费** | 每张图约 1000-3000 tokens |
| **建议** | 控制分辨率，避免过大图片 |

---

## 六、与其他方案对比

| 维度 | API 识别 | Sharp 本地 |
|------|----------|------------|
| **依赖** | 无需 | 需 libvips |
| **准确性** | 高（模型理解） | 中（仅像素处理） |
| **速度** | 5-60s | <1s |
| **网络** | 需联网 | 离线可用 |
| **适用场景** | 内容理解、OCR | 图像裁剪、格式转换 |

---

## 七、故障排查

### 问题 1：API 超时

```python
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        pass
except urllib.error.URLError as e:
    print(f"超时: {e}")
    # 重试机制
```

### 问题 2：Base64 编码错误

```python
# 错误：重复编码
base64_image = base64.b64encode(image_data).decode('utf-8')  # 正确
# base64_image = base64.b64encode(base64_image).decode('utf-8')  # 错误！

# 验证图片可读
try:
    with open(image_path, 'rb') as f:
        data = f.read()
    assert len(data) > 0
    print(f"图片大小: {len(data)} bytes")
except Exception as e:
    print(f"读取失败: {e}")
```

### 问题 3：响应字段为空

```python
msg = data.get("choices", [{}])[0].get("message", {})
reasoning = msg.get("reasoning", "") or ""
content = msg.get("content", "") or ""

final = reasoning if reasoning else content
if not final:
    print("⚠️ 模型返回为空，检查请求格式")
```

---

## 八、最佳实践

1. **优先使用推理结果** — reasoning 字段包含详细分析，content 可能为空
2. **合理设置 max_tokens** — 建议 2000-4000，避免截断
3. **控制图片大小** — 长图裁剪关键区域再识别
4. **串行调用** — 避免并发触发限流
5. **缓存结果** — 同一图片多次分析可缓存结果

---

*本文档由小智制定，后续修改按此标准执行。*
