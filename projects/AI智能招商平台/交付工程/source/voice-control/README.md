# 语音控制模块

## 模块说明
实现大屏交互控制，将语音指令转化为演示操作。

## 功能列表
- 语音翻页控制
- 视频播放/暂停控制
- 内容放大/缩小
- 页面切换
- 多轮对话管理

## 目录结构
```
voice-control/
├── controller/         # 语音控制器
│   ├── command.py      # 命令解析
│   └── dispatcher.py   # 命令分发
├── presentation/       # 演示控制
│   ├── slide_manager.py  # 幻灯片管理
│   └── media_player.py   # 媒体播放
├── dialog/             # 对话管理
│   └── multi_turn.py   # 多轮对话
└── main.py             # 服务入口
```
