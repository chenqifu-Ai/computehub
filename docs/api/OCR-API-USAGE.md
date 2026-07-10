# OCR API 使用文档

**端点**: `POST /api/v1/ocr`  
**监控**: `GET /api/v1/ocr/stats`  
**基础**: Tesseract 5.3.4 (chi_sim + eng)  
**Gateway**: `http://127.0.0.1:8282` (本地) 或 `http://36.250.122.43:8282` (公网)

---

## 快速开始

### 1. 识别一张图片

```bash
# 图片 → base64 → POST
IMG_B64=$(base64 -w0 screenshot.jpg)

curl -s -X POST http://127.0.0.1:8282/api/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$IMG_B64\"}"
```

**返回示例**:
```json
{
  "success": true,
  "data": {
    "text": "Hello ComputeHub OCR!",
    "language": "chi_sim+eng",
    "duration_ms": 194,
    "success": true
  }
}
```

### 2. 指定语言

```bash
# 纯英文
curl -s -X POST http://127.0.0.1:8282/api/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$IMG_B64\",\"lang\":\"eng\"}"

# 纯中文
curl -s -X POST http://127.0.0.1:8282/api/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$IMG_B64\",\"lang\":\"chi_sim\"}"

# 中英混合（默认）
curl -s -X POST http://127.0.0.1:8282/api/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$IMG_B64\",\"lang\":\"chi_sim+eng\"}"
```

### 3. 设置超时

```bash
# 大图片或并发场景建议 30s+
curl -s -X POST http://127.0.0.1:8282/api/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$IMG_B64\",\"timeout\":30}"
```

### 4. 查看统计

```bash
curl -s http://127.0.0.1:8282/api/v1/ocr/stats
```

```json
{
  "success": true,
  "data": {
    "total_runs": 86,
    "total_chars": 1197,
    "avg_ms": 214
  }
}
```

---

## 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|:------:|------|
| `image` | string | ✅ | — | Base64 编码的图片数据 (JPEG/PNG) |
| `lang` | string | ❌ | `chi_sim+eng` | Tesseract 语言代码，多个用 `+` 连接 |
| `timeout` | int | ❌ | `30` | 超时秒数，建议 ≥30 |

## 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 请求是否成功 |
| `data.text` | string | 识别出的文本 |
| `data.language` | string | 使用的语言 |
| `data.duration_ms` | int | 耗时 (毫秒) |
| `error` | string | 失败时的错误信息 |

---

## 各语言调用示例

### Python

```python
import base64, requests

def ocr_image(image_path, lang="chi_sim+eng", timeout=30):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    resp = requests.post(
        "http://127.0.0.1:8282/api/v1/ocr",
        json={"image": b64, "lang": lang, "timeout": timeout}
    )
    return resp.json()

# 使用
result = ocr_image("screenshot.png")
print(result["data"]["text"])
```

### Node.js

```javascript
const fs = require('fs');

async function ocrImage(imagePath, lang = 'chi_sim+eng') {
  const b64 = fs.readFileSync(imagePath).toString('base64');
  const resp = await fetch('http://127.0.0.1:8282/api/v1/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: b64, lang, timeout: 30 })
  });
  return resp.json();
}

ocrImage('screenshot.png').then(r => console.log(r.data.text));
```

### Go

```go
package main

import (
    "bytes"
    "encoding/base64"
    "encoding/json"
    "io"
    "net/http"
    "os"
)

type OCRRequest struct {
    Image   string `json:"image"`
    Lang    string `json:"lang"`
    Timeout int    `json:"timeout"`
}

func ocrImage(path, lang string) (string, error) {
    data, _ := os.ReadFile(path)
    b64 := base64.StdEncoding.EncodeToString(data)
    
    body, _ := json.Marshal(OCRRequest{
        Image:   b64,
        Lang:    lang,
        Timeout: 30,
    })
    
    resp, _ := http.Post("http://127.0.0.1:8282/api/v1/ocr",
        "application/json", bytes.NewReader(body))
    defer resp.Body.Close()
    
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    
    text := result["data"].(map[string]interface{})["text"].(string)
    return text, nil
}
```

---

## 从 Agent 调用

所有 Agent（小智、米智、端智等）可通过 ComputeHub 任务分发调用 OCR：

```json
{
  "action": "http",
  "method": "POST",
  "url": "http://127.0.0.1:8282/api/v1/ocr",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "image": "<base64_image_data>",
    "lang": "chi_sim+eng",
    "timeout": 30
  }
}
```

---

## 性能参考

| 场景 | 耗时 | 说明 |
|------|:---:|------|
| 单次英文 (400×100) | ~200ms | 最快场景 |
| 单次中文 (400×100) | ~260ms | 中文字符更多 |
| 单次中英混合 | ~420ms | 双语言包 |
| 多行文本 (400×200) | ~620ms | 面积更大 |
| 5 并发 (30s timeout) | 16-25s | CPU 串行排队 |

> ⚠️ Tesseract 是 CPU 密集型，并发请求会排队。建议客户端 timeout ≥ 30s。

---

## 常见问题

**Q: 返回空文本？**  
A: 图片过于模糊或文字太小。建议图片分辨率 ≥ 300 DPI，文字高度 ≥ 20px。

**Q: 并发超时？**  
A: 增大 timeout 参数到 30s+。或减少并发数。

**Q: 支持哪些图片格式？**  
A: JPEG、PNG、BMP、TIFF 均可（Tesseract 原生支持）。

**Q: 图片大小有限制吗？**  
A: 当前无硬限制，但建议 ≤ 10MB。超大图片会占用大量 CPU 和内存。
