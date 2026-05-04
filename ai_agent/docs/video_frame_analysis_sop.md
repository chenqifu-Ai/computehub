# 视频帧分析标准流程 SOP

## 一、功能说明
- ffmpeg 从视频中均匀抽取指定帧
- AI 视觉模型逐帧分析（描述场景、物体、颜色、图案、构图）
- 输出结构化结果（JSON + Markdown）

## 二、标准调用命令

```bash
# 标准调用（高精度，默认 3 帧）
python3 /root/.openclaw/workspace/ai_agent/code/video_frame_analysis.py <视频路径>

# 快速模式（8B 模型，每帧 ~5s）
python3 /root/.openclaw/workspace/ai_agent/code/video_frame_analysis.py <视频路径> --model 8b

# 自定义帧数和时长
python3 /root/.openclaw/workspace/ai_agent/code/video_frame_analysis.py <视频路径> --frames 5 --duration 5

# 自定义分析提示
python3 /root/.openclaw/workspace/ai_agent/code/video_frame_analysis.py <视频路径> --prompt "分析画面中的文字内容"
```

## 三、模型选择

| 模型 | 精度 | 每帧耗时 | 适用场景 |
|------|------|---------|---------|
| qwen3-vl:235b | 高精度 | ~45s | 精细分析、文档识别 |
| qwen3-vl:8b | 快速 | ~5s | 快速预览、批量处理 |

## 四、输入输出规范

### 输入
- 视频格式：mp4 / avi / mov / webm
- 帧数建议：2-5 帧（3 帧默认，覆盖视频开头/中间/结尾）
- 时长建议：3-10 秒（不超过视频实际时长）

### 输出
- JSON：`results/video_frame_analysis/analysis_YYYYMMDD_HHMMSS.json`
- Markdown：`results/video_frame_analysis/analysis_YYYYMMDD_HHMMSS.md`

## 五、使用示例

```bash
# 分析一段 5 秒视频，抽取 3 帧
python3 ai_agent/code/video_frame_analysis.py test.mp4 --frames 3 --duration 5

# 快速预览
python3 ai_agent/code/video_frame_analysis.py test.mp4 --model 8b --frames 2
```

## 六、注意事项
- 每帧传输 base64 数据约 100-150KB，注意带宽
- 235B 模型有 API 请求间隔限制，批量处理需串行
- 第一帧含模型加载时间，后续帧更快
- 视频时长必须 ≥ duration 参数
