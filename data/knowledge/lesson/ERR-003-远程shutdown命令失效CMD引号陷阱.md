# Knowledge: ERR-003: 远程shutdown命令失效（CMD引号陷阱）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows, CMD, 引号陷阱, shutdown, 远程执行, ERR-003
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 问题
通过OPC向Windows Worker发送 shutdown /r /t 5 /c "注释" 命令返回completed但没重启

## 根因
CMD的/C参数和shutdown的/c参数冲突
中文逗号在CMD中被视为参数分隔符
外层引号被CMD吃掉一层，shutdown收到残缺参数
shutdown默默忽略无法解析的参数，exit 0退出

## 安全写法
shutdown /r /t 0  — 不加注释，干净利落
shutdown /r /t 5 /c "注释不要用中文和逗号"  — 转义引号
powershell -Command "Restart-Computer -Force"  — 最稳

## 核心教训
向Windows远程执行命令时，CMD的引号/特殊字符解析是最大陷阱

完整文档: memory/topics/错误记录/远程shutdown失效-中文引号问题.md
