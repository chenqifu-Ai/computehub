# Knowledge: OCR API 使用文档
> Type: skill
> Source: 小智
> Confidence: 1.0
> TTL: 30 days
> Tags: ocr, api, tesseract, 文字识别, computehub
> Timestamp: 2026-07-06T08:34:27+08:00

## Content

端点: POST /api/v1/ocr — Tesseract 文字识别
监控: GET /api/v1/ocr/stats
Gateway: http://127.0.0.1:8282 (本地) 或 http://36.250.122.43:8282 (公网)
Tesseract: 5.3.4 (chi_sim + eng)

参数:
- image (必填): base64 编码的图片 (JPEG/PNG)
- lang (默认 chi_sim+eng): 语言代码，纯英文用 eng，纯中文用 chi_sim
- timeout (默认 30): 超时秒数，并发建议 30s+

Python 调用:
  import base64, requests
  b64 = base64.b64encode(open("screenshot.png","rb").read()).decode()
  r = requests.post("http://127.0.0.1:8282/api/v1/ocr",
      json={"image": b64, "lang": "chi_sim+eng", "timeout": 30})
  print(r.json()["data"]["text"])

Node.js 调用:
  const fs = require("fs");
  const b64 = fs.readFileSync("screenshot.png").toString("base64");
  const r = await fetch("http://127.0.0.1:8282/api/v1/ocr", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({image:b64, lang:"chi_sim+eng", timeout:30})
  });
  console.log((await r.json()).data.text);

性能参考:
- 单次英文 ~200ms，中文 ~260ms，中英混合 ~420ms
- 5 并发排队约 16-25s（Tesseract CPU 密集，串行执行）
- 客户端 timeout 建议设 30s+

注意事项:
- 图片建议 ≥ 300 DPI，文字高度 ≥ 20px
- 严重模糊图片会返回空文本（预期行为）
- 支持 JPEG/PNG/BMP/TIFF 格式
- 建议图片 ≤ 10MB

测试结果 (2026-07-06): 14/14 测试通过，可投入生产使用。
