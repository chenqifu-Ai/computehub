# WIN-PID-001: Windows 精准 PID 进程管理与零停机升级标准流程

**版本**: v1.0  
**创建**: 2026-06-23  
**场景**: 同一台 Windows 物理机跑多个 worker 节点时，精准识别 PID→node_id 映射，实现零停机升级

---

## 1. 背景

同一台 Windows 物理机（如 DESKTOP-9LBEMBA）可能运行多个 ComputeHub worker 进程，每个对应不同的 node_id。直接 `taskkill /F /IM computehub.exe` 会误杀所有进程，必须通过 PID 精准击杀。

## 2. 核心流程

### 2.1 查进程列表（带详细信息）

```bash
# 通过任意在线节点发任务
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<在线节点>",
    "command":"tasklist /FI \"IMAGENAME eq computehub*\" /V /FO CSV",
    "timeout":15
  }'
```

**关键参数说明**:
- `/V` — 显示详细信息（CPU 时间、用户名等）
- `/FO CSV` — CSV 格式输出，方便解析
- `/FI "IMAGENAME eq computehub*"` — 通配符匹配 `computehub.exe` 和 `computehub_new.exe`

### 2.2 查节点注册时间

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/nodes/list' | python3 -c "
import json,sys
d = json.load(sys.stdin)
for n in d['data']:
    if '<关键词>' in n['node_id']:
        print(f\"{n['node_id']:20s} | {n['status']:8s} | {n['registered_at']}\")
"
```

### 2.3 交叉比对：PID → node_id 映射

| 数据源 | 字段 | 比对依据 |
|--------|------|---------|
| `tasklist /V` | 进程启动时间 | ≈ 节点注册时间 |
| `nodes/list` | `registered_at` | 节点注册时间戳 |

**映射规则**: 进程启动时间 ≈ 节点注册时间（误差 < 30s），时间最接近的即为对应关系。

### 2.4 精准杀进程

```bash
# 通过另一个在线节点发 kill 命令（目标进程不能杀自己）
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<另一个在线节点>",
    "command":"taskkill /F /PID <目标PID>",
    "timeout":15
  }'
```

### 2.5 验证

```bash
# 确认只剩预期进程
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<在线节点>",
    "command":"tasklist /FI \"IMAGENAME eq computehub*\" /FO CSV /NH",
    "timeout":15
  }'
```

## 3. 零停机升级流程（先启新，再杀旧）

### 3.1 下载新 binary

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"curl -o D:\\computehub\\computehub_new.exe http://<GATEWAY>:8282/api/v1/download?file=computehub-windows-amd64.v<版本>.exe",
    "timeout":120
  }'
```

### 3.2 启动新进程（不同 binary 名）

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"start /B D:\\computehub\\computehub_new.exe worker --agent --gw http://<GATEWAY>:8282 --node-id <node_id> --interval 3 --concurrent 4 --heartbeat 10",
    "timeout":15
  }'
```

**⚠️ 注意**: `start /B` 后必须跟空字符串 `""` 作为窗口标题参数，否则 cmd 会把 exe 路径当标题：
```cmd
start /B "" D:\computehub\computehub_new.exe worker --agent ...
```

### 3.3 等待新进程注册（~5s）

```bash
sleep 5
curl -s 'http://<GATEWAY>:8282/api/v1/nodes/list' | python3 -c "
import json,sys
d = json.load(sys.stdin)
for n in d['data']:
    if '<关键词>' in n['node_id']:
        print(f\"{n['node_id']:20s} | {n['status']:8s} | {n['registered_at']}\")
"
```

### 3.4 查进程列表，确认新旧 PID

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"tasklist /FI \"IMAGENAME eq computehub*\" /V /FO CSV",
    "timeout":15
  }'
```

### 3.5 杀旧进程

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"taskkill /F /PID <旧PID>",
    "timeout":15
  }'
```

### 3.6 清理旧 binary

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"del D:\\computehub\\computehub.exe && rename D:\\computehub\\computehub_new.exe computehub.exe",
    "timeout":15
  }'
```

### 3.7 最终验证

```bash
curl -s 'http://<GATEWAY>:8282/api/v1/tasks/submit' \
  -X POST -H 'Content-Type: application/json' \
  -d '{
    "node_id":"<目标节点>",
    "command":"tasklist /FI \"IMAGENAME eq computehub*\" /FO CSV /NH",
    "timeout":15
  }'
```

## 4. 关键原则

| 原则 | 说明 |
|------|------|
| **先启新，再杀旧** | 零停机窗口，服务不中断 |
| **不同 binary 名** | 避免同名进程冲突，方便区分新旧 |
| **PID 精准击杀** | 不误杀新进程或其他节点进程 |
| **注册时间交叉验证** | 进程启动时间 ≈ 节点注册时间，确认新进程已上线再动手 |
| **跨节点杀进程** | 目标进程不能杀自己，需通过另一个在线节点发 kill 命令 |

## 5. 常见问题

### 5.1 `start /B` 不生效
**现象**: 命令返回成功但新进程没启动  
**根因**: cmd 把 exe 路径当窗口标题参数  
**修复**: `start /B "" D:\path\to\exe.exe args...`

### 5.2 进程启动时间与注册时间不匹配
**原因**: 进程可能先启动但网络延迟导致注册延迟  
**处理**: 允许 ±30s 误差，取最接近的匹配

### 5.3 杀进程后节点状态未更新
**原因**: Gateway 心跳超时机制（默认 30s）  
**处理**: 等待 30s 后重新查 `nodes/list`

---

## 6. 实战案例（2026-06-23）

**场景**: DESKTOP-9LBEMBA 上 xingke-work01 / xingke-work02 两个节点

**进程列表**:
```
"computehub.exe","12168","Console","2","15,328 K","DESKTOP-9LBEMBA\PC","0:00:04"
"computehub.exe","11348","Console","2","22,408 K","DESKTOP-9LBEMBA\PC","0:00:05"
```

**节点注册时间**:
```
xingke-work02 | 2026-06-23T13:53:28
xingke-work01 | 2026-06-23T14:13:59
```

**映射结果**:
| PID | 启动时间 | 内存 | 对应节点 |
|-----|---------|------|---------|
| 12168 | ~13:53 | ~15 MB | xingke-work02 |
| 11348 | ~14:13 | ~22 MB | xingke-work01 |

**操作**: 通过 xingke-work01 发 `taskkill /F /PID 12168` 杀掉 xingke-work02 的进程 ✅
