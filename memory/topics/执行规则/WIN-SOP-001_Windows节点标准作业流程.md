# WIN-SOP-001: Windows 节点标准作业流程（SOP）

> 建立时间: 2026-06-24  
> 版本: v1.0  
> 来源: work-softpark 故障复盘  
> 适用范围: 所有 Windows 节点的接入、维护、修复

---

## 1. 节点接入流程

### 1.1 接入前检查

| 序号 | 检查项 | 命令 | 通过标准 |
|------|--------|------|---------|
| 1 | 节点可达 | `echo OK` | exit=0 |
| 2 | Shell 可用 | `echo hello && echo alive` | 正常执行 |
| 3 | PowerShell 可用 | `where powershell` | 返回完整路径 |
| 4 | curl 可用 | `where curl` | 返回完整路径 |
| 5 | Node.js 可用 | `C:\Users\<user>\node\node.exe --version` | 返回版本号 |
| 6 | 磁盘空间 | `wmic logicaldisk get caption,freespace` | 剩余 ≥ 3 倍 |

> ⚠️ **铁律**: 接入检查只读，不杀任何进程。

### 1.2 首次部署

```
1. 上传 binary 到 D:\computehub\ (或指定目录)
2. 验证 binary 完整性 (certutil -hashfile SHA256)
3. 手动启动 Worker 测试
4. 验证 Gateway 端能看到节点上线
5. 注册为 Windows 服务 (sc create)
6. 设置故障恢复策略 (sc failure)
7. 验证服务启动成功 (sc query → STATE: 4 RUNNING)
8. 验证 Gateway 端心跳正常
```

### 1.3 注册服务（必须步骤）

```bash
# 1. 确认没有同名服务
sc.exe query work-softpark-worker 2>nul

# 2. 如果有旧服务，先删除
sc.exe delete work-softpark-worker 2>nul

# 3. 创建服务 (注意 = 后必须有空格)
sc.exe create work-softpark-worker binpath= "D:\computehub\computehub-windows-amd64.exe worker --agent --gw http://36.250.122.43:8282 --node-id work-softpark --concurrent 4 --heartbeat 10 --interval 3" start= auto displayname= "WorkSoftpark Worker"

# 4. 设置故障恢复策略
sc.exe failure work-softpark-worker reset= 86400 actions= restart/5000/restart/10000/restart/30000

# 5. 启动服务
sc.exe start work-softpark-worker

# 6. 验证服务启动成功
sc.exe query work-softpark-worker
# 确认输出: STATE: 4  RUNNING

# 7. 验证 Gateway 端心跳
# Gateway 日志应显示: [Kernel] 🔁 Auto-registering node work-softpark
```

### 1.4 接入验证清单

| 验证项 | 命令 | 通过标准 |
|--------|------|---------|
| 服务状态 | `sc.exe query work-softpark-worker` | STATE: 4 RUNNING |
| 进程运行 | `tasklist | findstr computehub` | 进程存在 |
| 端口监听 | `netstat -ano | findstr 8383` | 端口 8383 LISTENING |
| Gateway 注册 | `grep work-softpark /home/computehub/gateway.log` | 注册日志 |
| 心跳正常 | 检查 Gateway 日志心跳间隔 | ≤ 10 秒 |

---

## 2. 操作权限分级

### 2.1 权限定义

| 权限等级 | 执行人 | 适用场景 |
|---------|--------|---------|
| 🔴 **P0 核心操作** | 端智亲自 | 节点注册/注销服务、Binary 替换、Gateway 配置 |
| 🟡 **P1 常规操作** | 达智 | 状态检查、简单命令执行、文件查询 |
| 🟢 **P2 只读操作** | 达智 | `echo`、`dir`、`where`、`ps`、`netstat` |

### 2.2 禁止达智执行的操作

**🚫 绝对禁止达智执行以下操作：**

| 操作 | 原因 |
|------|------|
| `taskkill /F` | 杀死进程会导致节点离线 |
| `sc.exe delete` | 删除服务会导致服务丢失 |
| `sc.exe start/stop` | 停止服务会导致服务不可用 |
| Binary 替换 | 替换 binary 可能导致执行失败 |
| `netsh` | 修改防火墙可能影响网络连接 |
| `reg add/del` | 修改注册表可能影响系统配置 |

### 2.3 允许达智执行的操作

| 操作 | 说明 |
|------|------|
| `echo OK` | 节点可达性检查 |
| `dir` / `ls` | 文件列表查询 |
| `where` | 命令路径查询 |
| `tasklist` | 进程列表查询 |
| `netstat -ano` | 端口监听查询 |
| `sc.exe query` | 服务状态查询 |
| `nvidia-smi` | GPU 信息查询 |
| `systeminfo` | 系统信息查询 |
| `ipconfig /all` | 网络信息查询 |
| `type` | 文件内容读取 |

### 2.4 端智亲自执行的操作

| 操作 | 说明 |
|------|------|
| `sc.exe create` | 注册 Windows 服务 |
| `sc.exe delete` | 删除 Windows 服务 |
| `sc.exe start/stop` | 启动/停止服务 |
| Binary 下载/上传 | 通过 Gateway API 分发 |
| Binary 替换 | 通过 Gateway 任务下发 |
| 服务故障恢复策略 | `sc.exe failure` |
| 防火墙规则修改 | `netsh` |
| 注册表修改 | `reg add/del` |

---

## 3. 操作前确认清单

### 3.1 所有操作前必须确认

| 序号 | 确认项 | 说明 |
|------|--------|------|
| 1 | **操作目的** | 为什么要做这个操作？ |
| 2 | **影响范围** | 会影响哪些节点/服务？ |
| 3 | **失败预案** | 失败了怎么恢复？ |
| 4 | **执行人** | 谁执行？（端智亲自 or 达智） |
| 5 | **权限等级** | P0/P1/P2？ |
| 6 | **操作清单** | 每一步操作都列出来 |
| 7 | **验证步骤** | 怎么确认操作成功？ |

### 3.2 操作前输出格式

```
🔍 [操作前确认]
① 目的: [为什么要做这个操作]
② 影响: [会影响谁]
③ 预案: [失败了怎么恢复]
④ 执行人: [端智亲自 / 达智]
⑤ 权限: [P0/P1/P2]

操作清单:
1. [第一步操作]
2. [第二步操作]
3. [第三步操作]

验证:
1. [怎么确认成功]
2. [怎么确认失败]
```

### 3.3 操作后验证清单

| 验证项 | 命令 | 通过标准 |
|--------|------|---------|
| 服务状态 | `sc.exe query <service>` | STATE: 4 RUNNING |
| 进程运行 | `tasklist | findstr <process>` | 进程存在 |
| 端口监听 | `netstat -ano | findstr :PORT` | 端口 LISTENING |
| Gateway 注册 | `grep <node-id> gateway.log` | 注册日志 |
| 心跳正常 | 检查 Gateway 日志心跳间隔 | ≤ 10 秒 |

---

## 4. 节点离线应急预案

### 4.1 预案触发条件

| 条件 | 触发级别 | 响应时间 |
|------|---------|---------|
| 节点离线 5 分钟 | 🟡 P2 | 15 分钟内响应 |
| 节点离线 15 分钟 | 🟠 P1 | 10 分钟内响应 |
| 节点离线 30 分钟 | 🔴 P0 | 5 分钟内响应 |
| 多个节点同时离线 | 🔴 P0 | 立即响应 |

### 4.2 预案流程

```
节点离线
  │
  ├─ Step 1: 确认离线原因
  │   ├─ 检查 Gateway 日志: grep <node-id> gateway.log
  │   ├─ 检查 Worker 日志: tail -20 worker.log
  │   └─ 检查系统日志: journalctl -u computehub-worker
  │
  ├─ Step 2: 判断离线原因
  │   ├─ 进程被杀 → 重启进程
  │   ├─ 服务异常 → sc.exe start <service>
  │   ├─ 网络中断 → 检查网络连接
  │   └─ 其他 → 收集日志后上报
  │
  ├─ Step 3: 恢复操作
  │   ├─ 手动重启: D:\computehub\computehub-windows-amd64.exe worker --agent ...
  │   ├─ 服务重启: sc.exe start <service>
  │   └─ 二进制替换: 通过 Gateway API 分发
  │
  └─ Step 4: 验证恢复
      ├─ 检查 Gateway 日志: grep <node-id> gateway.log
      ├─ 检查心跳: 确认节点心跳间隔 ≤ 10 秒
      └─ 通知: 更新 HEARTBEAT.md 状态
```

### 4.3 各操作系统恢复命令

| 操作系统 | 手动启动命令 | 服务重启命令 |
|---------|-------------|-------------|
| Windows | `D:\computehub\computehub-windows-amd64.exe worker --agent --gw http://36.250.122.43:8282 --node-id <node-id>` | `sc.exe start <service>` |
| Linux | `/home/computehub/ComputeHub/deploy/computehub worker --agent --gw http://127.0.0.1:8282 --node-id <node-id>` | `sudo systemctl start computehub-worker` |
| macOS | `/Users/<user>/computehub/computehub-darwin-amd64 worker --agent --gw http://36.250.122.43:8282 --node-id <node-id>` | `launchctl start com.computehub.worker` |

### 4.4 预防性措施

| 措施 | 说明 | 责任人 |
|------|------|--------|
| 所有 Windows 节点必须注册为服务 | 注册为 Windows 服务，确保自动重启 | 端智 |
| 所有 Linux 节点必须配置 systemd | 配置 systemd 服务，确保自动重启 | 端智 |
| 心跳监控 | 每分钟检查 Gateway 节点在线状态 | 达智 |
| 离线告警 | 节点离线 5 分钟自动告警 | 端智 |
| 定期巡检 | 每天检查所有节点服务状态 | 端智 |

---

## 5. 附录

### 5.1 常用命令速查

```batch
# 节点检查
echo OK
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
wmic logicaldisk get caption,freespace

# 进程检查
tasklist | findstr computehub
netstat -ano | findstr :8383

# 服务管理
sc.exe query <service-name>
sc.exe start <service-name>
sc.exe stop <service-name>
sc.exe delete <service-name>

# 文件操作
dir C:\computehub\
certutil -hashfile C:\computehub\computehub.exe SHA256
```

### 5.2 节点信息表

| 节点 | 操作系统 | 服务状态 | 备注 |
|------|---------|---------|------|
| ecs-p2ph | Ubuntu | systemd | Gateway + Worker |
| wanlida-opc01 | Windows | Windows 服务 | GPU RTX 4060 |
| wanlida-ubuntu | Ubuntu | systemd | 达智 Agent |
| xingke-work01 | Windows | Windows 服务 | - |
| windows-mobile01 | Windows | Windows 服务 | - |
| work-softpark | Windows | **待注册** | 需要注册服务 |
| local-arm | Android | 手动 | 端智 Node |

### 5.3 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-24 | v1.0 | 初版，基于 work-softpark 故障复盘 |

---

*本文档由端智编写，2026-06-24。持续更新中。*
