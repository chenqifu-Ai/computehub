# Knowledge: Gallery 移动端截图 OCR 深度分析方法论

> Type: knowledge
> Verified: 2026-07-04
> Author: agent

## Problem

移动端通过 AI 大厅上传的截图（.jpg），需要分析其中的文字和内容。
直接 `read` 工具读取图片时，图像数据被模型处理，但需要精确的文字提取和深度分析。
特别是 Android 浏览器截图（com.android.browser），包含深色模式 UI，文字提取困难。

## Solution

### 方法：OCR 全文提取 + 结构化分析

**步骤 1：定位图片文件**

```bash
# 查找 Gallery 中的截图文件
find /home/computehub/gallery/ -name "Screenshot_*.jpg" -type f | head -5
# 或通过 API 查看文件列表
curl -s http://localhost:8282/api/v1/files/ 2>/dev/null
```

**步骤 2：保存为 PNG（OCR 兼容性更好）**

```bash
python3 << 'EOF'
from PIL import Image
img = Image.open("/path/to/screenshot.jpg")
img.convert("RGB").save("/tmp/screenshot.png", "PNG")
EOF
```

**步骤 3：Tesseract OCR 提取文字**

```bash
# 常用 PSM（Page Structure Mode）：
#   3  — 全自动（默认）
#   4  — 单列文本
#   6  — 统一块文本（推荐移动端截图）
#  11  — 稀疏文本

tesseract /tmp/screenshot.png stdout --psm 6 -l chi_sim+eng
```

**步骤 4：多 PSM 模式尝试**

```python
for psm in ["3", "4", "6", "11"]:
    subprocess.run(
        ["tesseract", img_path, "stdout", f"--psm={psm}", "-l", "chi_sim+eng"],
        capture_output=True, text=True
    )
```

**步骤 5：结构化分析**

将 OCR 结果按区域组织：
- 顶部状态栏（时间、信号、电量）
- 标题/导航栏
- 主体内容区域
- 底部提示/按钮

### 注意事项

1. **深色模式**：图片文字可能对比度低，OCR 识别率下降
2. **中文 + 英文混合**：必须使用 `chi_sim+eng` 双语言包
3. **PSM 模式选择**：移动端截图通常是全屏，`--psm 6`（统一块）效果最好
4. **分辨率**：全面屏截图分辨率高（如 2712x1220），可能需要缩放到 1000-1500 宽度以提高 OCR 精度
5. **文件格式**：JPG 转 PNG 再 OCR 兼容性更好（避免 JPEG 压缩伪影）
6. **Tesseract 安装**：
   ```bash
   apt-get install tesseract-ocr tesseract-ocr-chi-sim python3-pil
   ```

### 分析框架

拿到 OCR 结果后，按以下维度分析：

1. **上下文推断**：截图文件名含时间戳和 App 名（如 `com.android.browser`），提供时间和场景线索
2. **功能模块识别**：侧边栏/导航栏 → 当前页面归属
3. **用户行为推测**：搜索关键词 → 用户的意图和痛点
4. **系统状态提取**：状态栏 → 网络、电量、运行状态
5. **对比分析**：同一用户的多次截图对比 → 行为轨迹和变化
6. **问题发现**：与预期 UI 对比 → 发现 Bug 或设计问题

## Edge Cases

- **纯图片截图**（无文字）：OCR 返回空，需要用视觉模型分析
- **验证码/图形化界面**：OCR 无法识别图形元素
- **滚动长截图**：内容被截断，需确认是否完整
- **动态内容**（弹幕、动画）：静态截图无法捕捉变化
- **隐私信息**：截图可能含敏感数据，分析后应清理
