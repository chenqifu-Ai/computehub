# WIN-CMD-001: Windows 远程执行含二进制输出的命令标准流程

**版本**: v1.0  
**日期**: 2026-06-12  
**状态**: 定稿  
**负责人**: 端智

---

## 📋 问题背景

在 Gateway 任务系统中向 Windows 节点执行命令时，存在三个核心障碍：

1. **`cmd.exe` 双引号吞噬**: Gateway 的包装层会处理 `"` 字符，导致含 `"` 的命令被截断
2. **stdout 超长被截断**: `nvidia-smi` 等命令输出较长，Gateway 的 stdout buffer/timeout 会截断
3. **PowerShell -EncodedCommand 限制**: 编码内容是脚本体，不是文件路径，直接执行.bat 内容会被 PowerShell 解析报错

---

## ✅ 推荐方案：Base64 + certutil -decode → node.exe

### 核心思路

```
base64(JS脚本) → certutil -decode 写入临时文件 → node.exe 执行 → execFileSync() 绕过 cmd
```

**为什么有效**：
- `certutil -decode` 是 Windows 原生工具，不依赖 PATH
- `node.exe execFileSync()` 完全绕过 cmd.exe 的 stdout 限制
- base64 是纯 ASCII，不会被任何层转义

---

## 📦 标准模板

### 场景 1: 执行 nvidia-smi 获取 GPU 信息

#### 第一步：准备 JS 脚本

```javascript
// gpu_query.js
var cp = require('child_process');
var fs = require('fs');
var r = cp.execFileSync('nvidia-smi', { encoding: 'utf8' });
fs.writeFileSync('C:\\temp\\gpu_result.txt', r, 'utf8');
console.log('OK ' + r.split('\n')[1].trim());
```

#### 第二步：生成 base64

```bash
# 在 Mac/Linux 上生成
b64=$(base64 -w0 gpu_query.js)
echo "$b64"
```

或者 Python：

```python
import base64
script = r"""var cp=require('child_process');var fs=require('fs');
var r=cp.execFileSync('nvidia-smi',{encoding:'utf8'});
fs.writeFileSync('C:\\temp\\gpu_result.txt',r,'utf8');
console.log('OK '+r.split('\n')[1].trim());"""
print(base64.b64encode(script.encode('utf-8')).decode('ascii'))
```

#### 第三步：提交任务

```bash
# 完整命令链
cmd="echo $b64 > C:\\temp\\script.b64 && certutil -decode C:\\temp\\script.b64 C:\\temp\\script.js && C:\\Users\\admin\\node\\node.exe C:\\temp\\script.js && type C:\\temp\\gpu_result.txt"

curl -s -X POST http://<gateway-host>:<port>/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d "{\"node_id\":\"<node-id>\",\"command\":\"$cmd\",\"timeout\":30,\"priority\":8}"
```

#### 第四步：获取结果

```bash
sleep 15
curl -s "http://<gateway-host>:<port>/api/v1/tasks/detail?task_id=<task_id>" | python3 -c "
import sys,json; d=json.load(sys.stdin); dd=d.get('data',{})
print(dd.get('stdout',''))
"
```

---

### 场景 2: 执行任意命令（不限于 nvidia-smi）

**关键原则**：JS 脚本中只调用 `execFileSync`，**不直接使用双引号**（因为 `-e '...'` 里的内容会被 cmd 处理）。

#### 模板

```javascript
var cp = require('child_process');
var fs = require('fs');

// 执行命令
var r = cp.execFileSync('<命令>', ['<参数1>', '<参数2>'], {
    encoding: 'utf8',
    timeout: 60000
});

// 写入结果文件
fs.writeFileSync('C:\\temp\\<输出文件名>', r, 'utf8');

// 简单确认
console.log('DONE');
```

**示例 - 查磁盘空间**：

```javascript
var cp = require('child_process');
var fs = require('fs');
var r = cp.execFileSync('wmic', ['logicaldisk', 'get', 'caption,freespace,size'], { encoding: 'utf8' });
fs.writeFileSync('C:\\temp\\disk.txt', r, 'utf8');
console.log('DONE');
```

**示例 - 查进程**：

```javascript
var cp = require('child_process');
var fs = require('fs');
var r = cp.execFileSync('tasklist', ['/v', '/FO', 'CSV'], { encoding: 'utf8' });
fs.writeFileSync('C:\\temp\\processes.txt', r, 'utf8');
console.log('DONE');
```

---

## 📝 关键规则

### 1. 路径规则

| 路径 | 是否必须 | 说明 |
|------|----------|------|
| `C:\Users\admin\node\node.exe` | ✅ 必须 | 不用 node.exe -e，而是执行 .js 文件 |
| `C:\temp\` | ✅ 必须 | 临时文件统一放这里，确保可写 |
| `certutil.exe` | ✅ 不需要 | Windows 自带，PATH 里一定有 |

### 2. 引号规则

- **JS 脚本内部**：用单引号 `'`，不要用双引号 `"`（会被 Gateway 层处理）
- **路径中的反斜杠**：必须写 `\\\\`（JSON 一层 + cmd 一层）
- **命令参数**：用数组 `['arg1','arg2']`，不用拼接字符串

### 3. Timeout 规则

- Gateway `timeout`：30-60s（根据命令耗时）
- Node `execFileSync` timeout：60000ms（60s）
- 超长的命令（如 `nvidia-smi`）可能需 5-10s，设 30s 足够

### 4. 错误处理

JS 脚本应该加 try-catch：

```javascript
var cp = require('child_process');
var fs = require('fs');
try {
    var r = cp.execFileSync('nvidia-smi', { encoding: 'utf8' });
    fs.writeFileSync('C:\\temp\\gpu_result.txt', r, 'utf8');
    console.log('OK');
} catch (e) {
    fs.writeFileSync('C:\\temp\\gpu_result.txt', 'ERROR: ' + e.message, 'utf8');
    console.log('ERROR: ' + e.message);
}
```

---

## 🚫 已知限制

| 限制 | 说明 | 替代方案 |
|------|------|----------|
| Node.js 非系统 PATH | 不在 `C:\Windows\System32\cmd.exe` 的 PATH 里 | 用完整路径 `C:\Users\admin\node\node.exe` |
| certutil -decode 格式 | 只认 base64（UTF-8），不认 base64(-w0) 自动换行 | Windows 的 certutil 能自动忽略换行 |
| 文件写入权限 | 需在 `C:\temp\` 下写入 | 确保 temp 目录存在 |

---

## 📊 各方案对比

| 方案 | 双引号处理 | stdout 完整 | 执行速度 | 推荐度 |
|------|-----------|-------------|----------|--------|
| `cmd /C nvidia-smi` | ✅ | ❌ 被截断 | 快 | ⭐⭐ |
| `powershell -EncodedCommand` | ✅ | ✅ | 中 | ⭐⭐⭐ |
| `certutil -decode → node` | ✅ | ✅ | 快 (190ms) | ⭐⭐⭐⭐⭐ |
| `node.exe -e '...'` | ❌ 被处理 | ✅ | 快 | ❌ |
| `certutil -decodebase64` | ✅ | ✅ | 快 | ❌ 参数名错误 |

---

## 🔗 相关文件

- `WIN-STD-001_Windows软件安装标准流程.md` — Windows 远程软件安装
- `WIN-REPL-001_WindowsSystem32Binary替换标准流程.md` — System32 binary 替换

---

*本文档由端智编写，2026-06-12 定稿。基于实际验证的 5 个方案对比得出。*
