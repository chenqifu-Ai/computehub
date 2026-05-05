# Sprint 5: 生产就绪

**开始**: 2026-05-05
**目标**: 使 ComputeHub 具备生产部署能力

## Sprint 5.1 — Docker 生产化 ✅ → 进行中

### 任务
- [ ] 多阶段构建优化（go version pin + layer cache）
- [ ] 健康检查增强（依赖检查 + 端口检查）
- [ ] 日志轮转配置
- [ ] docker-compose 生产 profile（资源限制、healthcheck）
- [ ] .env 配置文件支持
- [ ] docker-compose.prod.yml 独立配置

### 验收标准
- `docker compose -f docker-compose.prod.yml up -d` 一键启动生产环境
- 健康检查 100% 通过
- 日志自动轮转（>10MB 切割）

## Sprint 5.2 — 自动化压测脚本 ✅ → 待执行

### 任务
- [ ] API 端点压测脚本（并发 + 持久连接）
- [ ] 节点接入模拟（自动注册 + 心跳 + 任务提交）
- [ ] 性能基线报告生成
- [ ] CI-ready 格式输出

### 验收标准
- 50/100/200/400 并发压力测试通过
- 输出 JSON 格式报告
- 支持 `make test` 一键运行

## Sprint 5.3 — API 文档 ✅ → 待执行

### 任务
- [ ] 所有 API 端点文档化
- [ ] 请求/响应示例
- [ ] 错误码表
- [ ] OpenAPI 3.0 spec

### 验收标准
- docs/API.md 完整覆盖所有端点
- 每个端点有 curl 示例
- 错误码表完整

## Sprint 5.4 — 部署手册 ✅ → 待执行

### 任务
- [ ] 生产部署步骤
- [ ] 配置文件说明
- [ ] 故障排查指南
- [ ] 监控告警配置

### 验收标准
- 新用户按手册可独立完成部署
- 常见问题 covered

## 依赖项（阻塞）
- 🔴 PAT 需添加 `Contents: Read+Write` + `Actions: Read+Write`（手动创建）
- 🔴 远程 GPU 机器 Worker Agent 部署（需地址确认）
