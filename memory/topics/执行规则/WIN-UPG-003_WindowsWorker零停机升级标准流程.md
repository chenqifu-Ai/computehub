# WIN-UPG-003 v3.2 — Windows Worker 零停机升级标准流程

**更新**: 2026-06-23 19:10  
**基于**: v3.1(18:50复盘) + 老大指令：唯一通道、确认清楚再走、不瞎想办法  
**核心原则**: **每步确认通过才走下一步**。方案对了就不换，失败先查环境不查语法。

---

## 🚨 铁律（先读，后动手）

### 🔴 铁律 1：Gateway deploy 目录检查

**动手前先确认：Gateway 实际跑的是哪个 deploy/ 目录？**

```bash
# 查 systemd 配置
systemctl cat computehub-gateway | grep ExecStart

# 查进程真实路径
ls -la /proc/$(pgrep -x computehub | head -1)/exe 2>/dev/null

# 对比 upgrade API 返回的 SHA 和磁盘实际文件
curl -s "http://GW:8282/api/v1/upgrade/check?platform=windows/amd64"
sha256sum <deploy-dir>/windows-amd64/computehub.exe
# → 两个 SHA 必须一致，不一致 = deploy 目录弄错了
```

**踩坑 2026-06-23**: `~/OPC/deploy/` 和 `~/ComputeHub/deploy/` 两个目录，Gateway 跑的是后者。改了前者半天没反应。

### 🔴 铁律 2：下载只用 `/api/v1/download`，不用 Gallery

```
http://GW:8282/api/v1/download?file=computehub.exe&platform=windows/amd64
```

不是 `/api/v1/files/`。Gallery 接口可能返回不同内容。

### 🔴 铁律 3：& 在命令里是 PowerShell 调用运算符，不是 cmd 分隔符

**踩坑 2026-06-23 — xingke-work01**: 有些 Windows Worker 用 PowerShell 包装所有 task 命令。PowerShell 把 `&` 当调用运算符，cmd 的 `&` 命令分隔符失效。

**症状**：
- exit_code=1，stdout 空
- stderr：`The ampersand (&) character is not allowed`
- stderr 出现 `out-file : FileStream was asked to open a device that was not a file` → 无害噪音，忽略

**修复**：整个命令用双引号包住传给 cmd：
```
# ❌ 错（PowerShell 吃 &）
"command": "echo HELLO & ver"

# ✅ 对
"command": "cmd /c \"echo HELLO && ver\""
```

### 🔴 铁律 4：唯一通道 = Gateway 任务提交，禁止走其他通道

**🚫 禁止** 通过 SSH、WMI、RDP、远程桌面、或其他非 Gateway 通道连接目标节点。

**原因**：
- 唯一通道才有统一的日志、审计、重试、超时处理
- SSH 通道不稳定（ECS SSH 间歇断连）、WMI 有权限/防火墙问题
- Gateway 通道自带心跳检测和节点状态追踪

**✅ 正确做法**：所有操作（下载、校验、启动、杀进程）都通过 Gateway 提交 task 完成。

### 🔴 铁律 5：不通过 Worker 自己提交 kill task

**踩坑 2026-06-23**: 通过旧 Worker 执行 `taskkill /F /PID <自身PID>` → task 提交了但执行不完，永远看不到结果。

**规则**：
- 查进程（只读）→ 直接用目标节点自己查，安全
- 杀进程 → 必须通过**中转节点**（Linux 稳定节点优先）
- 绝不用 `taskkill /F /IM computehub.exe` → 无差别杀所有 computehub，新进程会一起死

### 🔴 铁律 6：方案已验证的，失败先查环境，不换方案

**踩坑 2026-06-23 18:50**: 第3步用文件传JSON是正确的方案（避开所有转义问题），exit_code=7 → 没查 exit_code 含义 → 去改转义 → 再转 SSH → 越走越偏。如果当时查了 exit_code 速查表，就知道是网络问题，等15s重试即可。

```
失败时的判断流程：

exit_code≠0
  │
  ├─ exit_code=7（curl: Failed to connect to host）
  │    → 网络问题，不是命令/方案问题！
  │    → 等15s重试，不换方案不改转义
  │
  ├─ exit_code=2（curl: option unknown / 参数解析错误）
  │    → 转义/引号嵌套问题
  │    → 检查JSON格式和引号嵌套
  │
  ├─ exit_code=0 但 stdout 空
  │    → 语法不匹配（PowerShell 吃掉了 & 或其他符号）
  │    → 加 cmd /c 包裹后再试
  │
  ├─ exit_code=1（命令执行失败）
  │    → stderr 有内容，看具体报错信息
  │    → 确认命令和路径是否存在
  │
  └─ "assigned node not registered"
       → 节点掉线了，不是方案问题！
       → 查 nodes/list 确认节点状态
       → 节点恢复后重试，不换方案
```

### 🔴 铁律 7：语法探测不可跳过（跳过=违规）

**必须在第1步做语法探测**，不做不准往下走。不要猜命令格式，直接测。
详见「第1步：语法探测」章节。

### 🔴 铁律 8：每条命令独立提交，不链式操作

**踩坑 2026-06-23**: 下载后链 `& echo DL_OK` 想一次验证 → 链被 PowerShell 吃掉了 → 以为下载失败，实际已成功。

**规则**：每一步单独提交，等结果确认后再走下一步。

---

## 📋 标准流程（12 步，每步带确认门禁）
（0. 预备 → 1. 语法探测 → 2. 查信息 → 3. 下载 → 4. 验证 → 5. 启动(含退火重试) → 6. 验活 → 7. 双确认 → 8. 杀旧 → 9. 验下线 → 10. 替换清理 → 11. 终验）

### 符号说明

| 符号 | 含义 |
|------|------|
| `GATE ❓` | 确认点：看结果，决定走/停 |
| `→ 失败` | 这步没通过，停止，排查 |
| `→ 通过` | 这步确认 OK，继续下一步 |

---

### 第 0 步：预备确认（全走 Gateway API，不碰任何 SSH）

**下午教训**：gateway间歇404/超时，但没先做稳定性检查就直接上手，失败时以为是命令问题。

#### 0.1 前置：Gateway 稳定性检查（新增）

**下午踩坑**：exit_code=7 连续5次，以为命令格式不对，其实是gateway网络不稳。

```bash
# 连发3次 health check，间隔2s
echo "=== Gateway 稳定性测试 ==="
for i in 1 2 3; do
  curl -s --connect-timeout 3 --max-time 5 "http://GW:8282/api/health" 2>&1
  sleep 2
done
```

**GATE ❓** 3次health check都返回200？
- ✅ 全部200 → 继续
- ❌ 任何一次失败 → **停！** Gateway不稳定，修复后再动手

#### 0.2 Gateway deploy 目录检查（走upgrade API，不SSH）

```bash
# 查 upgrade API 返回的 SHA 和版本
curl -s "http://GW:8282/api/v1/upgrade/check?current_version=0&platform=windows/amd64" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f\"latest_version: {d['data']['latest_version']}\")
print(f\"binary_size:    {d['data']['binary_size']} bytes\")
print(f\"sha256:         {d['data']['sha256']}\")
"
```

→ API有返回且SHA不是空的 → deploy目录正常  
→ API返回500或空 → 新版本binary没放对位置，先部署

**GATE ❓** upgrade API返回正常（有版本号、SHA）？
- ✅ 正常 → 继续
- ❌ 异常 → **停！** 先把新版本binary部署到Gateway deploy目录

#### 0.3 确认目标节点在线（Gateway API）

```bash
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d.get('data',[]):
    print(f\"{n['node_id']:25s} | {n['status']:8s} | v{n.get('version','?'):10s} | {n.get('platform','?'):20s}\")
"
```

**GATE ❓** 目标节点 status = `online`？
- ✅ online → 继续（记下 platform 和 version）
- ❌ offline → **停，先排查节点为什么不在线**

#### 0.4 选中转节点（Gateway API）

```bash
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d.get('data',[]):
    if n['status']=='online':
        print(f\"  {n['node_id']:25s} | {n.get('platform','?'):20s}\")
"
```

**GATE ❓** 有可靠的 Linux 中转节点？
- ✅ 有 → 继续
- ❌ 没有 → **停，Windows 节点互相杀进程风险高，需要老大决策**

#### 0.5 确认新版本 binary 已就位

```bash
curl -s "http://GW:8282/api/v1/upgrade/check?current_version=0&platform=windows/amd64" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f\"latest_version: {d['data']['latest_version']}\")
print(f\"binary_size:    {d['data']['binary_size']} bytes\")
print(f\"sha256:         {d['data']['sha256']}\")
"
```

**GATE ❓** 有版本号、文件大小和 SHA 值？
- ✅ 有 → 继续
- ❌ 没有 → **停！** 新版本 binary 没准备好，先部署到 Gateway

#### 0.5 确定 node-id 方案

| 角色 | node-id 示例 | 说明 |
|------|-------------|------|
| 旧 Worker | `xingke-work01` | 当前运行的节点 |
| 新 Worker（临时） | `xingke-work01-new` | 先启动在新 binary 上测试 |
| 最终 Worker | `xingke-work01` | 杀旧 + 替换 binary 后恢复此名 |

**记下这三个名字**，后续步骤全部用这三个 node-id。

---

### 第 1 步：语法探测 — 确认目标节点的命令解释器

**为什么必需**：不同 Worker 的 task 包装方式不同（直接 cmd / PowerShell 包装 / 其他），命令语法不一样。**不要猜，直接测。**

#### 1.1 提交探测命令

```bash
# 提交一个最简单的 echo 命令
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "echo probe_check",
    "timeout": 10
  }'
```

→ 从返回的 JSON 中提取 `data.task_id`。记下来。

#### 1.2 等几秒后查 detail API

```bash
sleep 8
curl -s "http://GW:8282/api/v1/tasks/detail?task_id=<task_id>"
```

→ 看 `exit_code`, `stdout`, `stderr` 三个字段。

#### 1.3 分析结果

```
stdout="probe_check", exit_code=0, stderr=""  → 结论 A：直接 cmd，命令正常
stdout="", exit_code=1，stderr 包含 & 相关     → 结论 B：PowerShell 包装，需要 cmd /c "..."
stdout="", exit_code=1，stderr 别的错误         → 需要进一步排查
```

**结论 A 走法（直接 cmd）**：
```
SYNTAX_DIRECT=true
语法模板：命令直接写
例： "command": "echo xxx && dir C:\\tmp"
```

**结论 B 走法（PowerShell 包装）**：
```
SYNTAX_DIRECT=false
语法模板：命令用 cmd /c "..." 包住，内层 & 用双引号包
例： "command": "cmd /c \"echo xxx && dir C:\\tmp\""
```

**进一步确认结论 B（探测确认）：**
```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "cmd /c \"echo syntax_confirmed && ver\"",
    "timeout": 10
  }'
```

→ 等结果，看 stdout 是不是 "syntax_confirmed" + 版本信息。

**GATE ❓** 语法模板确认了吗？
- ✅ stdout 有预期内容 → 记下语法模板，后续所有命令用同一模式
- ❌ stdout 空或错误 → **停！** 不要猜语法，尝试其他格式或问老大

---

### 第 2 步：查旧 Worker 信息（只读，不碰任何东西）

#### 2.1 查 binary 路径和版本

```bash
# 提交到目标节点
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> where /R C:\\ computehub.exe && where /R D:\\ computehub.exe && <语法模板> <已知路径>\\computehub.exe version",
    "timeout": 15
  }'
```

→ 等结果，查 detail API。

**GATE ❓** 确认 binary 路径和版本了吗？
- ✅ `where` 找到了路径，`version` 输出了版本号 → 记下**正式路径**（如 `C:\computehub.exe` 或 `D:\computehub\computehub.exe`）
- ❌ `where` 找不到 → 试 `dir /s /b C:\computehub.exe` 搜索全盘
- ❌ `version` 跑不出来 → 看看 `tasklist` 的命令行参数能不能找到路径

#### 2.2 查 PID

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> tasklist /FI \"IMAGENAME eq computehub.exe\" /FO CSV /NH",
    "timeout": 15
  }'
```

→ 查 detail API。看有几个 computehub 进程，记下 PID。

**⚠️ 注意**：tasklist 的 `/FO CSV` 可能在不同系统表现不同，如果 stdout 空的，试试不带 `/V`：
```bash
"command": "<语法模板> tasklist /FI \"IMAGENAME eq computehub.exe\""
```

**GATE ❓** 确认 PID 了吗？
- ✅ 有 1 个 PID → 记下来
- ✅ 有 2 个 PID（异常情况，可能旧 Worker 重复启动了）→ 都记下来
- ❌ 找不到 PID → **停！** 目标节点显示 online 但没进程？查 Gateway 的心跳过期机制

#### 2.3 确认暂存目录

```bash
# 查 C: 盘有没有 tmp 目录
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> dir C:\\tmp",
    "timeout": 10
  }'
```

→ 如果 C:\tmp 不存在，换成 D:\tmp 或别的盘。

**GATE ❓** 确认 tmp 目录可用？
- ✅ 有可写目录 → 记下**下载路径**（如 `C:\tmp\ch_new.exe`）
- ❌ 所有 tmp 都不存在 → 用正式路径所在分区的 tmp（如 `D:\tmp\`）

---

### 第 3 步：下载新 binary

#### 3.1 提交下载任务

```bash
# 下载到暂存目录，不覆盖正式文件
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> curl -sL -o <下载路径\\ch_new.exe> \"http://GW:8282/api/v1/download?file=computehub.exe&platform=windows/amd64\"",
    "timeout": 300
  }'
```

→ 从响应提取 task_id。

**关键**：
- timeout=300s — 10MB+ binary 下载不能急
- URL 用双引号包住 → 防止 cmd 把 `&platform=` 当参数分隔符
- `-o` 的路径：`C:\tmp\ch_new.exe` 或 `D:\tmp\ch_new.exe`
- 如果目标节点没有 curl → 用 certutil（慢但可靠）：`certutil -urlcache -f http://... C:\tmp\ch_new.exe`

#### 3.2 查下载结果

```bash
sleep 15   # 等下载完成
curl -s "http://GW:8282/api/v1/tasks/detail?task_id=<task_id>"
```

**GATE ❓** 下载成功了吗？
- ✅ exit_code=0 → 继续
- ❌ exit_code≠0 → 查 stderr 看错误原因。网络问题？curl 不存在？

#### 3.3 验证文件存在和大小

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> dir <下载路径\\ch_new.exe>",
    "timeout": 15
  }'
```

→ 查 detail API。文件大小应当 ~10MB+。

**GATE ❓** 文件存在且大小合理？
- ✅ → 继续
- ❌ 文件不存在或大小为 0 → **删掉重下**

---

### 第 4 步：验证新 binary 完整性（关键确认点）

#### 4.1 SHA256 验证

```bash
# 在目标节点算 SHA
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> certutil -hashfile <下载路径\\ch_new.exe> SHA256 | findstr /i \"[0-9a-f]\"",
    "timeout": 15
  }'
```

→ 查 detail API，拿到 stdout 里的 SHA 值。

同时本地查 API 预期的 SHA：
```bash
curl -s "http://GW:8282/api/v1/upgrade/check?current_version=0&platform=windows/amd64" | python3 -c "import json,sys; d=json.load(sys.stdin); print('expected:', d['data']['sha256'])"
```

**GATE ❓** 两个 SHA 一致吗？
- ✅ 一致 → 继续
- ❌ 不一致 → **删掉 `ch_new.exe`，重新下载**。不用查原因，直接重下

#### 4.2 独立 version 验证

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> <下载路径\\ch_new.exe> version",
    "timeout": 15
  }'
```

→ 查 detail API。

**GATE ❓** version 输出是目标版本号吗？
- ✅ 版本号正确 → 继续。binary 完整可用 ✅
- ❌ 报错或无输出 → binary 损坏，**删掉重下**。不往下走

**清理损坏文件**：
```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> del /Q <下载路径\\ch_new.exe>",
    "timeout": 10
  }'
```

---

### 第 5 步：启动新进程（零停机关键）

**⚠️ 下午踩坑**：exit_code=7连续5次，以为是命令格式/转义问题，实际上就是网络不稳。换方向越陷越深。

**⚠️ 这一步是核心**：旧 Worker 仍然在线，用旧节点提交 task 启动新进程。新旧并存。

#### 5.1 生成启动命令（按语法探测结果分叉）

**结论 A（直接 cmd）**：
```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "start /B <下载路径\\ch_new.exe> worker --gw http://GW:8282 --node-id <目标节点>-new --interval 3 --concurrent 4 --heartbeat 10",
    "timeout": 15
  }'
```

**结论 B（PowerShell 包装）**：
```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "cmd /c \"start /B <下载路径\\ch_new.exe> worker --gw http://GW:8282 --node-id <目标节点>-new --interval 3 --concurrent 4 --heartbeat 10\"",
    "timeout": 15
  }'
```

⏱ **提交后不做任何别的操作**，等待10s让心跳注册。

#### 5.2 等心跳、查节点列表

```bash
sleep 10
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d.get('data',[]):
    if '-new' in n.get('node_id',''):
        print(f\"✅ NEW: {n['node_id']:25s} | {n['status']:8s} | v{n.get('version','?'):10s}\")
"
```

**GATE ❓** `-new` 节点出现且 status = `online`？
- ✅ 出现了 → **成功！** 进入第6步
- ❌ 没出现 → 进 **5.3 退火重试规则**

#### 5.3 退火重试规则（下午踩坑总结）

**下午犯的错**：exit_code=7不重试，而是换方案 → 越换越死。

```bash
# 重试计数器放在心里：最多重试3次
# 每次重试间隔15s

尝试次数 ≤ 3？→ 查本次的 exit_code：

exit_code=7（网络不通）
  └─ 等15s → 重新提交完全相同的命令 → 不换命令、不改转义

exit_code=2（参数错误）  
  └─ 检查JSON的引号嵌套 → 修正后立即重试 → 不隔

"assigned node not registered"
  └─ 节点掉线了 → 查 nodes/list → 等节点恢复再试

exit_code=0 但 stdout 空
  └─ PowerShell吃掉了 → 如果当前是结论A(直接cmd)，换结论B包裹
  └─ 如果已经是结论B(cmd /c)，查stderr

尝试次数 > 3？
  └─ **停了，不试了。向老大汇报：第5步连续失败3次**
  └─ 提供：尝试了什么方案、每次的exit_code和stderr
```

**GATE ❓** 重试次数 ≤ 3 且 exit_code 明确？
- ✅ 重试成功，新节点上线 → 继续
- ❌ 重试3次都失败 → **停！向老大汇报**

---

### 第 6 步：验证新 Worker 能干活
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>-new",
    "command": "echo new_worker_online",
    "timeout": 10
  }'
```

→ 查 detail API。

**GATE ❓** 新 Worker 成功返回 stdout？
- ✅ → 新 Worker 完全可用 ✅
- ❌ → 看错误。如果 task 提交失败 → 新 Worker 虽然注册了但可能内部异常

---

### 第 7 步：确认新旧都在线

```bash
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('--- 旧节点 ---')
for n in d.get('data',[]):
    if n['node_id']=='<目标节点>':
        print(f\"  {n['node_id']:25s} | {n['status']}")
print('--- 新节点 ---')
for n in d.get('data',[]):
    if n['node_id']=='<目标节点>-new':
        print(f\"  {n['node_id']:25s} | {n['status']}")
"
```

**GATE ❓** 两个都在线？
- ✅ 旧节点 `online` + 新节点 `online` → **可以杀旧的了**
- ❌ 旧节点已经不在了 → 说明自己挂了，跳过 kill 步骤
- ❌ 新节点不见了 → **停！** 新进程崩溃了，不能杀旧

---

### 第 8 步：精准杀旧进程

**🚫 不通过目标节点自己杀自己（task 永远回不来）**  
**🚫 不用 `/F /IM computehub.exe`（新进程也死）**  
**✅ 通过中转节点杀指定 PID**

#### 8.1 再次确认旧 PID（防止记错）

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>",
    "command": "<语法模板> tasklist /FI \"IMAGENAME eq computehub.exe\" /FO CSV /NH",
    "timeout": 15
  }'
```

→ 查 detail API。看有几个进程。两个进程（旧+新）→ 记下旧的那个 PID。

**GATE ❓** 确定哪个是旧 PID？
- ✅ 确认了 → 继续
- ✅ 只有一个进程 → 旧 Worker 已经自己挂了，直接跳到第 9 步
- ❌ 不确定哪个是旧 → 查启动时间或工作目录

#### 8.2 提交 kill 任务（通过中转节点）

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<中转节点>",
    "command": "<中转节点的语法> taskkill /F /PID <旧PID>",
    "timeout": 15
  }'
```

→ 查 detail API。

**GATE ❓** kill 成功了吗？
- ✅ exit_code=0 → 旧进程已杀 ✅
- ❌ exit_code≠0 → 但旧节点已经下线了也 OK，确认下一步

---

### 第 9 步：验证旧节点已下线

```bash
sleep 8
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d.get('data',[]):
    if '-new' in n.get('node_id',''):
        print(f\"✅ NEW: {n['node_id']:25s} | {n['status']}\")
    elif n['node_id']=='<目标节点>':
        print(f\"❌ OLD: {n['node_id']:25s} | {n['status']} (应该消失了)\")
"
```

**GATE ❓** 旧节点已经消失？
- ✅ 旧节点不在了，新节点 online → **零停机升级成功！** 🎉
- ❌ 旧节点还在 → 检查 kill 是否生效，可能需要重试 kill
- ❌ 新节点也不在了 → **紧急！两个都挂了！跳转到回滚预案**

---

### 第 10 步：替换 binary + 清理

#### 10.1 替换到正式路径

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>-new",
    "command": "<语法模板> move /y <下载路径\\ch_new.exe> <正式路径\\computehub.exe>",
    "timeout": 15
  }'
```

→ 查 detail API。

**GATE ❓** move 成功？
- ✅ exit_code=0 → 已替换 ✅
- ❌ 文件被占用 → 但新 Worker 跑的仍是 ch_new.exe，move 的是正式路径。可能旧路径文件已被占用（如果旧 Worker 没杀死前就占用着）。重试或跳过。

#### 10.2 清理临时文件

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>-new",
    "command": "<语法模板> if exist <下载路径\\ch_new.exe> (del /Q <下载路径\\ch_new.exe> & echo CLEANED) else (echo NONE)",
    "timeout": 10
  }'
```

→ 查 detail API。

---

### 第 11 步：最终验证

#### 11.1 节点列表确认

```bash
curl -s http://GW:8282/api/v1/nodes/list | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d.get('data',[]):
    print(f\"{n['node_id']:25s} | {n['status']:8s} | v{n.get('version','?'):10s} | {n.get('platform','?'):20s}\")
"
```

→ 版本号 = 目标版本 ✅，无重复 node-id ✅

#### 11.2 新 Worker 能力验证

```bash
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<目标节点>-new",
    "command": "echo upgrade_completed_successfully",
    "timeout": 10
  }'
```

→ 查 detail API。

**GATE ❓** 升级完成的标志？
- ✅ 旧节点下线 + 新节点 `online` + 版本号正确 + 任务能跑
- ✅ **升级完成！** 🎉

---

## 回滚预案

### 场景 A：第5步退火重试全部失败

**状态**：旧 Worker 没被杀，一切如常。新节点没注册上。

**操作**：
1. 清理 `ch_new.exe`（如果已下载）
2. **向老大汇报**：启动新进程连续失败3次
3. 提供每次的 exit_code、stdout、stderr

### 场景 B：第9步 — 旧被杀后，新 Worker 也死了（双亡紧急）

**状态**：目标节点 offline，目标节点-new 也不在。

**操作**：
```bash
# 用中转节点重新启动 Worker（原 node-id 直接启动）
curl -s -X POST http://GW:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "<中转节点>",
    "command": "<语法模板> start /B <下载路径\\ch_new.exe> worker --gw http://GW:8282 --node-id <目标节点> --interval 3 --concurrent 4 --heartbeat 10",
    "timeout": 15
  }'
```

→ 启动后等心跳，确认节点重新 online。

### 场景 C：第 10 步 — move binary 失败

**状态**：新 Worker 在跑（ch_new.exe），但正式路径的 binary 没更新。

**操作**：跳过 move，不影响运行。下次重启 Worker 时再处理。

### 场景 D：语法探测失败（第 1 步过不去）

**状态**：多种语法都试了，stdout 全是空的。

**操作**：**不猜了，找老大**。可能是 Worker 本身的任务执行器有问题，不是语法的问题。

---

## 📜 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-23 16:00 | 初版 |
| v1.1 | 2026-06-23 17:28 | 踩坑点、OS检查、timeout=300s |
| v2.0 | 2026-06-23 18:17 | Gateway deploy 目录、SHA 验证、中转节点、version 独立验证 |
| v2.1 | 2026-06-23 18:25 | PowerShell 包装探测、语法模板 |
| **v3.0** | **2026-06-23 19:45** | **全流程 GATE 门禁机制：每步提交→等结果→查detail API→确认→走下一步。不再猜结果、不再链式操作、不在失败时继续往下走。新增：回滚预案场景 D（语法探测失败）** |
| v3.1 | 2026-06-23 18:50 | 🔴 铁律 4(唯一通道)、🔴 铁律 6(失败先查环境不换方案+exit_code速查表)、🔴 铁律 7(语法探测不可跳过)。0.1前置gateway稳定性检查。去掉所有SSH。 |
| **v3.2** | **2026-06-23 19:10** | **第5步重写：按语法探测结论分叉(结论A/B)。新增5.3退火重试规则(最多3次+exit_code分支+3次全死就停向老大汇报)。第6步后移为验活。回滚场景A改为第5步失败汇报。老大明确唯一通道禁止走其他。** |
