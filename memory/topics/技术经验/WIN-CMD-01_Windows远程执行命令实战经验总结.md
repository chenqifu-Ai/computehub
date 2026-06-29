# WIN-CMD-01: Windows 远程执行命令实战经验总结

**版本**: v1.0  
**日期**: 2026-06-12  
**类型**: 技术复盘 + 经验总结  
**来源**: wanlida-opc01 节点全功能测试实战

---

## 🎯 背景

老大要求确认 wanlida-opc01 节点的 GPU 是否可用（RTX 4060 是否真的存在且能正常调用），需要远程执行 `nvidia-smi` 获取信息。

该节点通过 Gateway 任务系统管理，所有命令执行需经过三层代理：
1. **openclaw-tui** → Gateway API
2. **Gateway 包装层** → 把命令包在 PowerShell/cmd 里执行
3. **Windows 节点** → 实际执行环境

---

## 🔍 问题发现过程

### 第一轮：纯 cmd 执行 nvidia-smi

**尝试**: `curl .../tasks/submit -d '{"command":"nvidia-smi",...}'`

**结果**: ✅ 命令执行成功，但 stdout 被 Gateway 截断
- 耗时 5.4s，nvidia-smi 输出 38 行，超过 buffer 限制
- 只拿到部分输出，无法确认完整信息

### 第二轮：后台运行 + timeout

**尝试**: `timeout 3600 nvidia-smi > C:\temp\gpu.txt &`

**结果**: ❌ `nvidia-smi` 不支持 stdin，timeout 命令报错

### 第三轮：curl 后台下载 + node.exe

**尝试**: 用 curl 下载 nvidia 工具包，然后用 node.exe 调用

**结果**: ❌ curl 下载不稳定，120s timeout 不够

### 第四轮：node.exe -e 直接执行

**尝试**: `C:\Users\admin\node\node.exe -e "var cp=require('child_process')..."`

**结果**: ❌ 双引号被 Gateway 包装层吞噬
- `node.exe -e "console.log("hello")"` → `"` 被吞 → SyntaxError
- 所有含 `"` 的命令都会失败

### 第五轮：PowerShell -EncodedCommand

**尝试**: 将脚本编码为 PowerShell `-EncodedCommand` 参数

**结果**: ✅ 成功执行！但需要正确编码
- 关键发现：-EncodedCommand 编码的是脚本体，不是文件路径
- 直接用 cmd/bat 内容会被 PowerShell 解析报错（`@echo off` 被当作 PowerShell 代码）
- 需要通过 PowerShell 先写文件再执行

### 最终方案：Base64 + certutil -decode → node.exe

**核心流程**：
```
echo <base64> → certutil -decode → node.exe 执行 → execFileSync → type 结果
```

**为什么有效**：
1. **base64 是纯 ASCII** → 任何层都不会转义
2. **certutil -decode** → Windows 原生工具，不需要 PATH
3. **node.exe 执行 .js 文件** → 绕过 `node.exe -e` 的引号问题
4. **execFileSync()** → 完全绕过 cmd.exe 的 stdout 限制

---

## 📊 五方案对比

| 方案 | 双引号 | stdout | 速度 | 复杂度 | 结果 |
|------|--------|--------|------|--------|------|
| A: 纯 cmd/nvidia-smi | ✅ | ❌ 截断 | 快 | 简单 | ⭐⭐ |
| B: timeout+后台 | ❌ 不支持 | ❌ | - | 简单 | ⭐ |
| C: curl+node | ✅ | ✅ | 慢 | 中 | ⭐ |
| D: PowerShell -EncodedCommand | ✅ | ✅ | 快 | 高 | ⭐⭐⭐⭐ |
| **E: base64+certutil+node** | ✅ | ✅ | 极快(190ms) | 中 | ⭐⭐⭐⭐⭐ |

---

## 🧠 关键经验

### 经验一：三层代理的引号地狱

Gateway 到 Windows 之间有三层命令解释器：
1. JSON 层（`"` 转义）
2. cmd/PowerShell 包装层（`"` 吞噬）
3. Windows 内部命令层

**教训**: 永远不要假设双引号能穿透所有层。base64 是唯一安全的传输方式。

### 经验二：execFileSync 比 exec 可靠

- `child_process.exec()` → 通过 cmd.exe 执行，受 cmd 限制
- `child_process.execFileSync()` → 直接创建进程，绕过 cmd
- 需要 cmd 内置命令时（如 `dir`、`set`），用 `C:\Windows\System32\cmd.exe /C cmd_builtin`

### 经验三：PowerShell -EncodedCommand 的坑

- `-EncodedCommand` 接受的是 PowerShell **脚本代码**，不是文件路径
- 编码 bat/sh 内容会被 PowerShell 解析，导致语法错误
- 正确用法：编码 PowerShell 脚本，让脚本自己写文件再执行

### 经验四：certutil -decode 参数名

- ❌ `certutil -decodebase64` → 参数不存在
- ✅ `certutil -decode` → 正确参数
- 加上 `-f` 参数可以覆盖已存在的输出文件

### 经验五：Node.js 在 Windows 上的 PATH

- `C:\Users\admin\node\node.exe` 不在系统 PATH
- `nvidia-smi`、`wmic`、`tasklist` 在 PATH 里
- 但 `cmd.exe` 在 node execFileSync 中可能找不到（sandbox 限制）
- **原则**: node 脚本里调系统命令用相对/短路径，调 cmd 用绝对路径

---

## 📦 交付物

### 标准文档
- `memory/topics/执行规则/WIN-CMD-001_Windows远程执行含二进制输出命令标准流程.md`

### 工具脚本
- `scripts/win_cmd_executor.py` — 通用执行器
- `scripts/gpu_query.js` — GPU 查询
- `scripts/disk_query.js` — 磁盘查询
- `scripts/process_query.js` — 进程查询

### 验证结果
- wanlida-opc01: ✅ 10/10 全功能通过
- GPU: NVIDIA RTX 4060, 8188 MiB, 驱动 560.94, CUDA 12.6
- 节点状态: 可用作 GPU Worker

---

*本文档基于实际 5 轮尝试的真实记录整理。每一轮都记录了一次失败和一次学习。*
