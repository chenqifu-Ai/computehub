# Windows 节点统一部署标准 — windows-mobile

## 节点信息
| 项目 | 值 |
|------|------|
| 节点名 | windows-mobile |
| 角色 | 软智 |
| 机主 | 丁丁 |
| OS | Windows Server 2019 (10.0.17763) |
| 架构 | amd64 |
| IP | 112.48.104.210 |
| Gateway | 36.250.122.43:8282 |

## 安装路径

| 文件 | 路径 |
|------|------|
| Worker binary | `C:\Windows\System32\computehub.exe` |
| 启动脚本 | `C:\Windows\System32\start_worker.bat` |
| 下载缓存 | `C:\temp\computehub-v*.exe` |
| 自动更新 | 自动升级循环 (5min 间隔) |

## 开机自启

- **类型**: schtasks (onlogon)
- **任务名**: `ComputehubWorker`
- **执行**: `C:\Windows\System32\start_worker.bat`
- **用户**: SYSTEM
- **权限**: 最高 (HIGHEST)

## start_worker.bat 内容
```bat
@echo off
cd /d C:\Windows\System32
start /min computehub.exe worker --agent --gw http://36.250.122.43:8282 --node-id windows-mobile --interval 3 --concurrent 8 --heartbeat 10
```

## 启动参数说明
| 参数 | 值 | 说明 |
|------|-----|------|
| `--agent` | — | 启用智能体模式 |
| `--gw` | `http://36.250.122.43:8282` | Gateway 地址 |
| `--node-id` | `windows-mobile` | 节点标识 (14字符，安全) |
| `--interval` | 3 | 心跳间隔(秒) |
| `--concurrent` | 8 | 最大并行任务数 |
| `--heartbeat` | 10 | 心跳超时(秒) |

## 自动升级链路
```
Worker (5min轮询) → GET /api/v1/upgrade/check?platform=windows/amd64 → Gateway 返回最新版本 + SHA256
→ 下载 /api/v1/download?file=computehub.exe&platform=windows/amd64
→ SHA256验证 → 备份旧版 → 替换 binary → schtasks 重启
```

## 通信方式
- **主通道**: WebSocket (`/api/v1/ws`)
- **回退**: HTTP 长轮询
- **AI Hall**: WS 广播

## 历史清理
- ✅ OPC 旧目录已清理
- ✅ 无残留旧 backup
- ✅ 仅保留 System32 单一 binary

## 升级注意事项
1. 每次升级前先下载到 `C:\temp\computehub-v{version}.exe`
2. 用 schtasks 异步拉起 (不直接用 start /B，taskkill 会杀子进程)
3. 先下载再 taskkill (防覆盖运行中文件)
4. 路径始终用 `C:\Windows\System32\computehub.exe`