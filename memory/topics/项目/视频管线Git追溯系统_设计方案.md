# 🎬 视频管线 Git 全流程追溯系统 — 设计方案 v1.0

> 设计日期: 2026-05-19 | 状态: 待审批

---

## 一、项目背景

### 🔴 当前问题

```
用户提交PDF  ──→  ECS管线处理  ──→  产物进Gallery
      │                  │                │
      ▼                  ▼                ▼
  无记录             无日志归档          产物丢失不可追溯
```

具体案例：2026-05-19 凌晨提交「农产品流通大数据平台-厦门联农.pdf」，管线成功产出 `liangnong_liannong_v2.mp4`，但产物没出现在 Gallery 里，日志也没留，无法追溯到底是管线没写到 Gallery 目录，还是 Gallery 路径不匹配，还是被别的东西覆盖了。

### 🎯 核心目标

**让每一次视频生产任务都有迹可循**——从 PDF 提交 → 管线执行 → 产物产出 → Gallery 发布，全程 git 记录，任意历史任务可追溯、可复现、可审计。

---

## 二、系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        老大 (你)                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  命令: "做农产品联农的视频"                                     │   │
│  │  或: python3 submit.py 农产品联农.pdf                          │   │
│  └──────────────┬───────────────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  小智 (本地)                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ① 接收命令 → scp PDF 到 ECS                                 │   │
│  │  ② SSH执行 submit.py  触发管线 + 自动 git commit              │   │
│  │  ③ 验证产出 → 通知老大                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────────────┘
                  │ scp / ssh
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ECS 服务器 36.250.122.43                                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  /home/computehub/pipeline-repo/  ← Git 仓库 (核心)          │   │
│  │                                                                │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │   │
│  │  │  submit.py   │───▶│ video_pipe-  │───▶│ 产出自动进    │   │   │
│  │  │ (入口脚本)    │    │ line.py      │    │ Gallery       │   │   │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │   │
│  │         │                   │                   │            │   │
│  │         ▼                   ▼                   ▼            │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │  Git commit × 3 (每个阶段自动记录)                     │    │   │
│  │  │  commit 1: "任务: 农产品联农 v2 开始"                  │    │   │
│  │  │  commit 2: "产出: liangnong_liannong_v2.mp4 (12MB)"  │    │   │
│  │  │  commit 3: "发布: liangnong_v2.mp4 → Gallery"        │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Gallery  (8282端口)                                          │   │
│  │  /home/computehub/gallery/  ← 存放所有最终作品                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构（工程总览）

```
ECS 36.250.122.43 上的仓库:
/home/computehub/pipeline-repo/          ← 根目录
│
├── src/                                 ← 管线源代码（版本控制）
│   ├── video_pipeline.py                ← 主管线（已部署 v2.0）
│   ├── doc_parser.py                    ← PDF解析
│   ├── tts_engine.py                    ← TTS语音合成
│   ├── visual_templates.py              ← 可视化模板
│   ├── video_worker.py                  ← 工作节点
│   └── __init__.py
│
├── runs/                                ← 每次任务一个子目录（git 管理）
│   ├── manifest.json                    ← 全局索引
│   │
│   ├── 2026-05-18_world_chinese_foundation/  ← 已有任务归档
│   │   ├── manifest.json                ← 任务元数据
│   │   ├── run.sh                       ← 复现命令
│   │   ├── input/
│   │   │   └── manifest.json            ← 输入文件清单
│   │   ├── output/
│   │   │   └── manifest.json            ← 产出清单（大小、路径）
│   │   └── logs/
│   │       └── pipeline.log             ← 管线日志（大文件，gitignore）
│   │
│   ├── 2026-05-19_liangnong_liannong/   ← 丢失任务标记 status: lost_output
│   │   └── manifest.json                ← 记录"产物未进入Gallery"
│   │
│   └── 2026-05-19_xxx_new_task/         ← 新任务自动生成
│       ├── manifest.json
│       ├── run.sh
│       ├── input/
│       │   └── xxx.pdf                   ← 原始PDF（git lfs 或忽略）
│       ├── output/
│       │   └── xxx.mp4                   ← 成品视频
│       └── logs/
│           └── pipeline.log             ← 完整日志
│
├── tools/                                ← 管理工具
│   ├── submit.py                         ← [核心] 一键提交任务
│   ├── audit.py                          ← [核心] 查询历史
│   └── send_to_gallery.sh               ← 同步产物到 Gallery
│
└── README.md
```

---

## 四、核心流程图

### 4.1 一次完整任务的流程

```
 老大/小智                     pipeline-repo/                    Gallery
    │                               │                               │
    │  ① python3 submit.py          │                               │
    │  农产品联农.pdf -t "厦门联农"   │                               │
    │──────────────────────────────▶│                               │
    │                               │                               │
    │                               │  ② 复制PDF到 runs/.../input/   │
    │                               │  ③ git commit: "任务: 厦门联农   │
    │                               │     开始  pdf=xxx.pdf"         │
    │                               │                               │
    │                               │  ④ 调用 video_pipeline.py     │
    │                               │     - 解析PDF                  │
    │                               │     - 生成TTS                  │
    │                               │     - 视频合成                 │
    │                               │     - 写 pipeline.log          │
    │                               │                               │
    │                               │  ⑤ 产出 liangnong_v2.mp4      │
    │                               │     git commit: "产出: xxx.mp4 │
    │                               │     (12MB, 耗时5分12秒)"       │
    │                               │                               │
    │                               │  ⑥ 调用 send_to_gallery.sh    │
    │                               │──────────────────────────────▶│
    │                               │                               │
    │                               │  ⑦ git commit: "发布: xxx.mp4 │
    │                               │     → Gallery"                │
    │                               │                               │
    │  ⑧ 验证: ✓ Gallery 可看 ✓     │                               │
    │     git log 有记录             │                               │
    │◀──────────────────────────────│                               │
```

### 4.2 问题排查流程（以丢失案例为例）

```
假如 liangnong_liannong_v2.mp4 又不见了:

git log --oneline --grep="厦门联农"
  → commit A: "任务: 厦门联农 开始"
  → commit B: "产出: liangnong_liannong_v2.mp4"
  → commit X: "发布: liangnong_v2.mp4 → Gallery"  ❌ 没找到！

结论: 问题出在第⑥步（同步到 Gallery）
  → 检查 submit.py 中 send_to_gallery 的路径
  → 检查 Gallery 的 rootDir 配置
  → 直接修复
```

---

## 五、组件说明

### 5.1 `submit.py` — 任务提交入口

```bash
# 使用方式
python3 submit.py input.pdf \
    --title "农产品流通大数据平台" \
    --output-name liangnong_liannong_v2 \
    --pages 12

# 做了什么
1. 复制 PDF 到 runs/YYYY-MM-DD_任务名/input/
2. 生成 manifest.json + run.sh
3. git add && git commit "任务: xxx 开始"
4. 调用 video_pipeline.py 开始处理
5. 等待管线完成
6. 记录产出到 runs/.../output/
7. git add && git commit "产出: xxx.mp4 (12MB)"
8. 同步到 Gallery
9. git add && git commit "发布: xxx.mp4 → Gallery"
10. 输出来访链接
```

### 5.2 `audit.py` — 历史查询工具

```bash
# 查看所有任务
python3 audit.py list

# 输出:
# [2026-05-18] ✅ 世界华人基金会         → world_chinese_foundation_v3.mp4 (17MB)
# [2026-05-18] ✅ TTS管线测试 v2         → pipeline_tts_v2.mp4 (142MB)
# [2026-05-19] ❌ 农产品联农             → liangnong_liannong_v2.mp4 (丢失)

# 查看单个任务详情
python3 audit.py show 2026-05-19_liangnong_liannong

# 搜索关键字
python3 audit.py search "联农"

# 查看所有丢失的任务
python3 audit.py list --status lost
```

### 5.3 `pipeline_wrapper.sh` — 管线包装器

```bash
# 自动包裹在 submit.py 内部调用
# 在管线运行前后自动执行:
#   - 写 pipeline.log
#   - 记录开始/结束时间
#   - 计算耗时
#   - 自动 git commit
```

---

## 六、Git 提交规范

每次任务自动产生 3 次 git commit：

| 阶段 | Commit Message | 记录内容 |
|------|---------------|----------|
| 开始 | `task: 任务名 — 开始` | PDF 文件名、大小、参数 |
| 产出 | `output: xxx.mp4 — 完成` | 文件名、大小MB、耗时、管道日志摘要 |
| 发布 | `publish: xxx.mp4 → Gallery` | Gallery URL、是否成功 |

```bash
# 查看所有历史提交
git log --oneline

# 输出示例:
# bf1dfe4 init: pipeline-repo 结构初始化
# c9e82d5 feat: 管线代码 v2.0
# a1b2c3d archive: 5条历史任务归档
# d4e5f6g task: 厦门联农 — 开始
# h7i8j9k output: liangnong_liannong_v2.mp4 (12MB, 5分12秒)
# l0m1n2o publish: liangnong_v2.mp4 → Gallery
```

---

## 七、问题定位能力

### 7.1 产物丢失排查

```bash
# 情况1: 产物完全消失
git log --all --diff-filter=D -- "*.mp4"
  → 看到谁删了、啥时候删的

# 情况2: 产物从未进入 Gallery
git log --oneline | grep -i "publish"
  → 没有 publish commit → 第⑥步出问题
  → 检查 output commit 有没有 → 有的话产物还在 runs 目录

# 情况3: 产物被覆盖
git log --all -- "liangnong*"
  → 看到完整生命线: 创建→修改→删除
```

### 7.2 参数对比

```bash
# 对比两次同PDF不同参数的输出
git diff commit_A commit_B -- runs/联农/input/manifest.json
git diff commit_A commit_B -- runs/联农/manifest.json
```

### 7.3 全局搜索

```bash
git log --all --grep="联农"   # 找所有关联任务
git log --all --grep="丢失"   # 找所有出问题的
```

---

## 八、实施计划

| 阶段 | 内容 | 估算工时 |
|------|------|----------|
| **P0 已完成** | ECS 仓库初始化 + 管线代码入库 + 历史任务归档 | 已做完 |
| **P1** | `submit.py` 完整实现（提交→管线→commit→Gallery全自动） | 1.5h |
| **P2** | `audit.py` 查询工具 | 30min |
| **P3** | 管线包装器 + 自动日志收集 | 30min |
| **P4** | Gallery 双路径问题排查修复 | 30min |
| **P5** | 端到端测试 + 文档完善 | 30min |
| **总计** | | **~3h** |

---

## 九、风险和注意事项

1. **Git 仓库膨胀**: 二进制文件（mp4）通过 .gitignore 排除，只追踪 manifest 清单
2. **管线代码更新**: 修改 src/ 下的代码后，记得 git commit 版本号
3. **ECS 磁盘空间**: 当前 32G 可用，runs 目录只留 manifest，大文件在 Gallery 和临时目录
4. **ssh key 权限**: 已配置好，自动化流程无需输入密码

---

> **审批状态**: ⏳ 等待老大确认
> **下一步**: 你决定后，我按 P1→P5 顺序执行
