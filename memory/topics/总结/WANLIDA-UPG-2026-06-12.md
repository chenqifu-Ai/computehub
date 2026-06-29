# 总结：wanlida-opc01 升级 v1.3.25 → v1.3.30

**时间**: 2026-06-12 18:27 - 18:29  
**目标**: 将 wanlida-opc01 (183.251.21.92) 从 v1.3.25 升级到最新  
**结果**: ✅ 成功，升级至 v1.3.30

---

## 问题诊断

1. **Gateway 升级 API 不存在**: `/api/v1/worker/upgrade` 返回 404，没有推送式升级端点
2. **Worker 自动升级未生效**: wanlida-opc01 的 v1.3.25 Worker 可能：
   - 缓存中 skip 了之前的版本（upgrade_cache 问题）
   - 或 v1.3.25 版本没有 test-register 模式
3. **8383 端口不可达**: 从 ECS 无法直连 wanlida-opc01:8383

## 解决方案

采用 **EncodedCommand + exec task** 远程替换 binary：

1. **确认 download API**: `GET /api/v1/upgrade/check?node_id=xxx&platform=xxx` 返回 v1.3.30 可用
2. **生成 PowerShell EncodedCommand**: 用 base64(utf16-le) 编码，绕过 cmd 对 `$` 的解析
3. **Task 内容**:
   - Download 10.3MB binary from Gateway (`/api/v1/download?file=computehub.exe&platform=windows/amd64`)
   - Stop 旧 Worker 进程
   - 替换 `C:\computehub\computehub.exe`
   - 重启 Worker（带完整启动参数）
4. **提交 exec task**: `POST /api/v1/tasks/submit` with priority=8, timeout=180s

## 关键经验

### ✅ 有效方法
- **EncodedCommand** 绕过 cmd 变量解析（win-repl-001 核心规则）
- **submit task** 是远程 Windows 节点执行命令的标准路径
- **timeout=180s** 足够覆盖 10MB 下载 + 替换 + 重启

### ❌ 无效方法
- `certutil -urlcache` 下载大文件不稳定（可能 hang）
- `GET /api/v1/worker/upgrade` 端点不存在（404）
- 直接 TCP 连接 wanlida-opc01:8383（端口不通）

### ⚠️ 注意事项
- windows-mobile 路径是 `C:\ProgramData\computehub\` 而非 `C:\computehub\`
- windows-mobile 升级仍然卡在 1.3.28（路径不匹配导致）
- 后续需要针对 windows-mobile 用正确路径重试

## 全集群状态（升级后）

| 节点 | IP | 版本 | 状态 | 平台 |
|------|-----|------|------|------|
| ecs-p2ph | 36.250.122.43 | 1.3.30 | ✅ online | linux/amd64 |
| wanlida-opc01 | 183.251.21.92 | 1.3.30 | ✅ online | windows/amd64 |
| worker-arm | 36.248.233.20 | 1.3.29 | ✅ online | linux/arm64 |
| windows-mobile | 112.48.104.210 | 1.3.28 | ✅ online | windows/amd64 |

**待完成**: windows-mobile 升级到 v1.3.29+

## 后续 TODO

- [ ] windows-mobile 使用正确路径 `C:\ProgramData\computehub\` 重试升级
- [ ] 确认 windows-mobile 启动脚本/参数（有 `start-worker-mobile.sh`）
- [ ] 统一 deploy/version.txt 到最新（当前本地仍为 1.3.26）
