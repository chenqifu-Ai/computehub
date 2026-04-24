# ComputeHub - 算力出海平台

**项目状态**: 🟡 开发中  
**创建日期**: 2026-04-22  
**负责人**: 小智  
**核心目标**: 海外算力服务部署与管理平台

## 📁 目录结构

```
computehub/
├── README.md          ← 项目说明（本文件）
├── docs/              ← 文档
│   ├── computehub_详细开发计划.md    ← 8 周开发路线图
│   ├── send_computehub_plan_email.py ← 邮件通知脚本
│   └── compute_overseas_server_stack.md ← 海外服务器软件栈
├── code/              ← 源代码
│   ├── computehub/    ← 主代码（含 gateway + TUI 二进制）
│   ├── merge_computehub.py
│   ├── compute_overseas_landing.html
│   └── token_compute_overseas.html
├── deploy/            ← 部署包
│   └── computehub-opc-windows-deployment/
├── results/           ← 运行结果
│   ├── computehub_local.db
│   ├── computehub_dashboard.html
│   ├── computehub_api.log
│   └── computehub_gateway.log
└── scripts/           ← 工具脚本（待添加）
```

## 🎯 项目目标

提供算力资源出海的一站式解决方案，包括：
- 海外服务器部署与管理
- 算力资源调度与分配
- 前端仪表板与 API 服务
- OPC 协议集成

## 📊 开发进度

| 阶段 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 1 | 服务器软件栈设计 | ✅ 完成 | compute_overseas_server_stack.md |
| 2 | 开发计划制定 | ✅ 完成 | 8 周路线图 |
| 3 | 核心代码开发 | 🟡 进行中 | gateway + TUI |
| 4 | 前端开发 | 🟡 进行中 | landing page |
| 5 | 部署包制作 | 🔴 待开始 | OPC Windows 部署 |
| 6 | 测试与优化 | ⬜ 未开始 | - |

## 🔍 检索项目

```bash
# 查看项目文件清单
cd /root/.openclaw/workspace
git ls-files projects/computehub/

# 搜索项目内容
git grep -l "ComputeHub" projects/computehub/

# 查看项目历史
git log --all --oneline -- projects/computehub/
```

## 📝 开发规范

1. 所有代码和文档放在对应子目录
2. 每次开发完成后 `git add . && git commit`
3. 重大功能使用语义化版本号

---
*最后更新: 2026-04-24*
