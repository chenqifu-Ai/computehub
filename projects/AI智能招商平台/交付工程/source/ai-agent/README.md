# AI智能体模块

## 模块说明
本模块实现AI智能招商的核心AI能力：
- 在线/离线语音识别
- 自动讲解引擎
- 语音问答引擎
- 内容加密模块

## 目录结构
```
ai-agent/
├── voice/              # 语音识别/合成
│   ├── offline.py      # 离线语音识别
│   ├── online.py       # 在线语音识别
│   └── tts.py          # 语音合成
├── nlp/                # NLP引擎
│   ├── intent.py       # 意图识别
│   └── context.py      # 上下文管理
├── qa/                 # 问答引擎
│   ├── faq.py          # FAQ问答
│   └── llm.py          # LLM增强问答
├── encrypt/            # 内容加密
│   ├── aes.py          # AES加密/解密
│   └── drm.py          # DRM保护
├── presentation/       # 讲解引擎
│   └── engine.py       # 自动讲解引擎
└── main.py             # 服务入口
```

## API接口
- `POST /voice/recognize` - 语音识别
- `POST /voice/ask` - 语音问答
- `POST /presentation/start` - 启动讲解
- `POST /presentation/control` - 讲解控制

## 依赖
- Python 3.10+
- whisper / funasr
- pytorch
- edge-tts
