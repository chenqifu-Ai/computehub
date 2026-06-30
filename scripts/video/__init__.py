"""
🎬 ComputeHub Video Production Suite
Worker 内置模块 — 不通过 API 传输代码，只传参数

模块结构:
  doc_parser.py   — 文档解析 (PPTX/DOCX/PDF)
  tts_engine.py   — 语音合成 (edge-tts)
  video_pipeline.py — 视频编码引擎 (重构版)
  video_worker.py — Worker 入口（接收参数、执行、上报进度）
"""
__version__ = "1.0.0"
