# MEMORY.md - 长期记忆（精简版）

## 🏆 历史时刻：首次跨 Agent 通讯成功 (2026-06-20 15:41)
**事件**: 端智（Android ARM64）↔ 小智（ECS x86_64 Ubuntu）通过 OpenClaw `sessions_send` 首次成功握手
**物理隔离铁证**: 架构(ARM vs x86)、内核(Android vs Ubuntu)、hostname、machine-id 四维比对，SSH 直连交叉验证
**关键教训**: `sessions_send` timeout ≠ 失败（异步投递）；Agent 自报指纹不可靠，需独立验证链路
**后续**: Phase 2 集群管控（端智注册 Worker + 统一状态上报）待实施
**详情见**: `memory/2026-06-20.md`

## 🪟 System32 binary 替换陷阱 WIN-REPL-001 (2026-06-06)
**核心教训**: Windows System32 下的 Worker binary 替换必须走 PowerShell `-EncodedCommand`，避免 cmd 吃掉 `$` 变量
**标准文档**: `memory/topics/执行规则/WIN-REPL-001_WindowsSystem32Binary替换标准流程.md`
**关键规则**:
- cmd 把 `$var` 当环境变量：`powershell -Command "$url"` → cmd 吃掉 `$url`，值为空
- `certutil -urlcache` 下载 >5MB 文件不稳定，可能 hang 死 Worker
- 替换前必须 spawn 新进程（test-register 模式），防止 kill Worker → 断联
- MS 官方推荐做法：UTF-16LE → base64 → `powershell -EncodedCommand`
- 替换后需要等 Worker 重启恢复（~30s）

## 📧 邮件发送标准 STD-003 (2026-05-21 定稿)
**核心**: 所有发邮件任务统一走 `scripts/send_email.py`，禁止用其他方式
**配置文件**: `config/email.conf`（授权码来源）
**主授权码（QQ）**: `bzgwylbbrocdbiie`
**备用授权码（163）**: `AWZBPidhza74EbV8`
**自动切换机制**: QQ优先 → 163自动备选
**用法**: `python3 scripts/send_email.py <收件人> <主题> <内容文件路径>`
**规则**: 任何需要发邮件的场景（合同、报告、通知等）都调用此脚本，不再新建发送代码

## 用户信息
- **称呼**：老大
- **邮箱**：19525456@qq.com
- **备用邮箱**：3198880764@qq.com
- **时区**：Asia/Shanghai (GMT+8)

## 📦 Windows软件安装标准 WIN-STD-001 (2026-05-18)
**核心教训**: 远程 Windows 安装软件，PATH 不会自动更新、引号嵌套问题、msiexec 任务挂死
**详情见**: `memory/topics/执行规则/WIN-STD-001_Windows软件安装标准流程.md`
**关键规则**:
- 验证用完整路径 `C:\\Progra~1\\...` 而非 `python --version`
- ≥5 步的安装流程写 .py 文件 scp 到 ECS
- MSI 安装 timeout ≥ 120s
- 安装后手动 setx 补 PATH
- Go 1.26.3 + Python 3.11.6 已验证装在 `Windows-mobile-01`

## 🐛 技术经验：文件编辑精确匹配陷阱 (2026-04-20)
**核心教训**: `edit`工具要求完全精确匹配，包括所有空格和格式
**详情见**: `memory/topics/技术经验/文件编辑精确匹配陷阱.md`

## Ollama云端配置
- **服务器**: https://ollama.com
- **API Key**: 8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii
- **账号**: 19525456@qq.com
- **当前使用**: deepseek-v3.1:671b ✅

## 🚫 模型规则 (2026-06-18 锁定)
- **🔒 永久 primary**: `ollama-cloud-2/deepseek-v4-flash` — 老大明确锁定，不再变更
- **图片识别模型**: `zhangtuo-ai/qwen3.6-35b`（通过 base64 传图）⭐
- **我（端智）禁止** 修改 primary 或 session 模型 — 除非老大明确要求
- 可以临时切 session 测试别的模型，测完立即恢复
- ✅ 老大随时决定什么时候换

### 主力 API 配置 (zhangtuo-ai)
- **Provider**: `zhangtuo-ai`
- **模型 ID**: `qwen3.6-35b`（支持图片输入）
- **地址**: `https://ai.zhangtuokeji.top:9090/v1`
- **API Key**: `sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB`
- **状态**: ✅ 可用，~0.7s 响应
- **⚠️ 图片输入**: base64 → `image_url`，输出在 `reasoning` 字段
- **⚠️ max_tokens ≥ 1024**（推荐 2048~4096）
- **⚠️ content 永远为 null** — 从 `reasoning` 字段读取

### 废弃别名 (2026-06-04 停用)
| 旧名 | 原因 |
|------|------|
| `zhangtuo-ai-common/qwen3.6-35b-common` | 不支持图片输入，迁移至 zhangtuo-ai/qwen3.6-35b |
| `sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl` | 旧 key 已废弃 |

## ❌ Qwen 3.6 本地API (已停用)
- **旧地址**: http://58.23.129.98:8000/v1
- **旧模型**: qwen3.6-35b (深度推理模型)
- **旧配置已标记**: config/*.conf
- **已迁移至 NewAPI**: ai.zhangtuokeji.top:9090
- **已停用**: 2026-04-28 迁移至 NewAPI

## ✅ 当前主力 API 配置 (2026-06-04 更新)
- **地址**: https://ai.zhangtuokeji.top:9090/v1
- **Provider**: `zhangtuo-ai`
- **模型 ID**: `qwen3.6-35b`（含图片输入支持）
- **API Key**: `sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB`
- **⚠️ max_tokens ≥ 1024**（推荐 2048~4096）
- **⚠️ content 永远为 null**（输出全在 reasoning 字段）
- **响应速度**: ~0.7s（纯文本）/ 10-30s（含图片输入）
- **⚠️ IP 白名单**: 仅 ECS (36.250.122.43) 可直接访问；Windows 等走 Gateway LLM Proxy
- **废弃**: `zhangtuo-ai-common` / `sk-3RgMq1COL...` / `qwen3.6-35b-common`（2026-06-04 起停用）

## ✅ ActiveTasks 双倍递增 Bug 修复 (2026-06-02)
**根因**: `gateway_worker.go` 中 Worker 轮询时 `pending→running` 重复 `ActiveTasks++`
**修复**: 删除多余的那行 `state.Metrics.ActiveTasks++`
**文件**: `src/gateway/gateway_worker.go`

## ✅ Windows 节点升级为统一 binary (2026-06-02)
- **旧**: 旧 WMI agent（独立 binary，无自动升级）  
- **新**: `computehub.exe worker --agent` (v1.3.1, 10.6MB)
- **deploy 目录更新**: version.txt→1.3.1, sha256sums-1.3.1.txt, linux-amd64+windows-amd64 binary
- **结果**: `platform=windows/amd64` ✅，自带30分钟自动升级检查
- **关键教训**: Windows cmd 的 `&` 会截断 URL 参数，必须用 `"URL"` 包裹

## 🚀 ComputeHub 主工程 (2026-06-13 更新)
**🔒 老大明确锁定：所有精力集中于此工程**

- **路径**: `/data/data/com.termux/files/home/ComputeHub_new/` ⚡
- **版本**: v1.3.32
- **废弃路径**: `~/ComputeHub/`（旧克隆，不再使用）
- **远端仓库**: `ssh://computehub@36.250.122.43:8022/home/computehub/ComputeHub.git`
- **部署**: ECS 36.250.122.43:8282 (Gateway) + Workers

### v1.3.19 修复内容 (2026-06-08, commit c1e69f8)
- 🐛 **Worker升级传platform参数**: `DownloadWithChecksum` / `fetchSHA256` 都带 `&platform=linux/<arch>`，Gateway 返回正确的 binary
- 🐛 **Gateway checksum API接受platform**: 调用 `resolveSHA256ChecksumPlatform` 确保 arm64 Worker 查到 arm64 的 SHA256
- 🐛 **DNS修复** (远端 `8da821c`): composer 客户端自定义 DNS 解析器直查 `8.8.8.8`，绕过 Android `[::1]:53` 不可达

### ECS 部署关键信息
- **SSH**: `ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43`
- **systemd 服务**: computehub-gateway + computehub-worker (开机自启)
- **二进制路径**: systemd 用 `~/OPC/deploy/computehub`（WorkingDirectory=~/OPC）
- **deploy 目录**: `~/OPC/deploy/` (version.txt + 各平台子目录 + sha256sums-*.txt)

## 学习任务配置
- 各专家轮换学习任务已配置
- 学习内容写入各自技能目录的references/文件夹

## 用户偏好
- **自主性**: 有事自己解决，不要事事问
- **执行力**: 不要找借口，直接去做
- **禁止事项**: 严禁扫描其他电脑（如192.168.2.7, 192.168.2.29等）
- **效率**: 批量操作要一次性搞定

## 🔗 设备连接管理
**核心经验**: Token集中管理，设备唯一标识，跨网络识别
**详情见**: `memory/topics/技术经验/设备连接管理.md`

## 📋 默认执行规则（永久记忆 - 2026-04-11更新）
### 🎯 核心执行原则
1. **AI智能体SOP流程（7步法）**: 用户需求 → 智能分析 → 代码生成 → 自动执行 → 结果验证 → 学习优化 → 连续交付
2. **增强执行标准**: 极速响应(100ms)，精准理解(≥98%)，价值交付(≥90%)
3. **安全边界**: 安全 > 功能 > 效率，严禁越权操作

**完整规则见**: `memory/topics/执行规则/默认执行规则.md`

## 常见错误记录
### 重大安全事件 (2026-04-03)
- **问题**: 越权删除他人系统
- **教训**: 安全第一原则，严格权限边界，删除操作双重确认

**完整错误记录见**: `memory/topics/错误记录/常见错误.md`

## qwen3.6-35b API 格式异常 (2026-04-24) - ❌ 已解决
- 该模型 API 所有输出在 `reasoning` 字段，`content` 始终为 null
- 已适配层 `ai_agent/config/qwen36_adapter.py`
- **当前状态**: 已切换至 NewAPI，content 正常输出，不再需要适配层
- 旧文档见: `memory/topics/技术经验/qwen36-35b-api-format-fix.md`

## 当前持仓 (2026-06-26 更新)
| 股票 | 代码 | 数量 | 成本价 | 止损位 | 当前价 | 浮动盈亏 |
|------|------|------|--------|--------|--------|----------|
| 华联股份 | 000882 | 13,500股 | ¥1.873 | ¥1.60 | ¥1.33 | -29.00% (-¥6,760) |

**状态**: 🔴 止损位¥1.60已跌破超3个月，持续阴跌无反弹，需老大决策
**备注**: 华联股份从6/17的¥1.43跌至¥1.33，继续下行。整体账户盈利+15.62%（¥80,438总市值，¥69,569总投入），仓位8.0%。
**详情见**: `memory/topics/投资/当前持仓.md`

## 待办事项
- 邮件命令检查：已实现，可读取"小智请执行"邮件
- 小爱老师学习任务：执行中
- 各专家轮换学习：执行中

## 🧠 深度经验总结（2026-03-29）
### 五大核心能力资产
1. AI智能体框架: 148个Python脚本的系统引擎
2. 金融交易矩阵: 完整股票交易系统，可产品化
3. 商业双引擎: ChargeCloud + StockTrading 商业化产品
4. 专家知识生态: 56份文档，15万字知识库
5. 企业管理自动化: AI管理AI的元能力

**完整总结见**: `memory/topics/经验总结/深度经验总结.md`

## 🎯 Peter Steinberger 开源思维精髓（2026-04-09）
### 核心开源理念
1. **初心坚守**: 从简单工具开始，解决实际问题
2. **渐进演变**: 小步快跑，持续迭代升级
3. **社区驱动**: 响应真实需求，吸收集体智慧
4. **工程严谨**: 测试覆盖，配置规范，错误优雅

**完整思维见**: `memory/topics/学习总结/Peter_Steinberger思维.md`

## 🚀 三大核心经验规范（2026-04-11）
### 🎯 经验一：极速响应思维
- **1秒响应**: 任何操作必须在1秒内响应
- **0等待交互**: 用户无需等待，即时反馈
- **预加载机制**: 预测需求，提前准备资源

### 🎯 经验二：精准理解思维  
- **深度解析**: 理解字面背后的真实意图
- **上下文感知**: 基于对话历史精准理解
- **多维度分析**: 技术+业务+情感综合理解

### 🎯 经验三：价值交付思维
- **实质成果**: 每次交互都交付实际价值
- **效率优先**: 1小时当2小时用
- **问题解决**: 聚焦解决而非单纯回答

**完整规范见**: `memory/topics/执行规则/三大核心经验规范.md`

## 🏢 ChargeCloud充电云科技项目 (2026-03-21)
- **项目名称**: ChargeCloud - 充电桩运营管理SaaS平台
- **当前阶段**: 商业文档完成，等待开发启动
- **完成时间**: 2026-03-21

**项目详情见**: `memory/topics/项目/ChargeCloud充电云科技.md`

## 🚀 OpenRemoteAI 项目记录 (2026-03-27)
- **项目名称**: OpenRemoteAI - AI驱动远程连接优化系统
- **当前阶段**: 产品开发完成，准备部署
- **完成时间**: 2026-03-27 20:21

**项目详情见**: `memory/topics/项目/OpenRemoteAI项目记录.md`

## 🧠 深度思考总结 (2026-03-26)
### 工作回顾 (2026-03-25 至 2026-03-26)
#### 主要成就
1. **连续流技能系统创建**: 建立了TUI分析总结框架
2. **股票监控系统完善**: 建立了华联股份实时监控
3. **执行规则体系化**: 整合了AI智能体SOP流程

**完整思考见**: `memory/topics/经验总结/深度思考总结.md`

## 📊 公司项目现状记录 (2026-03-27 更新)
### 项目完成度统计
| 项目类型 | 完成度 | 状态 |
|----------|--------|------|
| AI智能体框架 | 85% | 持续优化 |
| 股票交易系统 | 80% | 生产使用 |
| 专家知识系统 | 75% | 建设中 |
| 自动化工具 | 70% | 完善中 |

**详细现状见**: `memory/topics/项目/公司项目现状.md`

## 🚀 装机技能系统 (2026-04-01)
### 部署流程
1. 设备连接检测
2. OpenClaw安装/更新
3. 配置初始化
4. 完整配置同步
5. 服务启动
6. 部署验证

**完整技能见**: `memory/topics/技术技能/装机技能系统.md`

## 📱 设备唯一识别系统 (2026-04-05)
### 🎯 核心概念
**设备指纹识别**: 不依赖易变的IP地址，使用设备固有属性进行识别

**设备标识**:
- **小米平板**: openclaw.local (192.168.1.19)
- **华为手机**: u0_a46/123 (HWI-AL00)
- **Windows笔记本**: xiaomi/1234567890 (192.168.1.7)

**完整系统见**: `memory/topics/技术技能/设备唯一识别系统.md`

## 🔧 SOP版本一致性修正 (2026-04-05)
### 问题发现
- **时间**: 2026-04-05 17:33
- **发现者**: 老大
- **问题**: AGENTS.md中的SOP流程描述与SOP.md不一致

**修正详情见**: `memory/topics/执行规则/SOP版本一致性修正.md`

## 🧠 智能体思想行为标准 (2026-04-09制定)
### 🎯 核心思想原则
1. **价值导向思维**: 每个行动都必须产生明确用户价值
2. **系统化思维**: 将复杂问题分解为可执行步骤
3. **成长型思维**: 视挑战为学习机会

**完整标准见**: `memory/topics/执行规则/智能体思想行为标准.md`

---
*此精简版保留核心记忆，详细内容请查看对应的主题文件*
*总字符数: 4982 (符合20000字符限制)*
*生成时间: 2026-04-23 08:15*