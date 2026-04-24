# 🚀 OpenClaw Workspace 远程 Git Clone 指南

> **版本**: v1.0 | **更新日期**: 2026-04-24 | **作者**: 小智 AI 助手

---

## 📌 仓库信息

| 项目 | 详情 |
|------|------|
| **仓库地址** | `https://github.com/chenqifu-Ai/openclaw-workspace.git` |
| **主要分支** | `computehub-qwen3.5-397b` |
| **备用分支** | `master` |
| **提交数** | 41+ |
| **认证方式** | HTTPS (GitHub Personal Access Token) |

---

## 📋 前提条件

### 1. 安装 Git

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y git

# CentOS/RHEL
sudo yum install -y git

# macOS
brew install git

# Windows
# 下载: https://git-scm.com/download/win

# Termux (Android)
pkg install git
```

### 2. 获取 GitHub 访问令牌

推荐使用 **Personal Access Token (PAT)**，比密码更安全：

1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 勾选权限：`repo` (完整控制私有仓库)
4. 生成并复制 Token
5. 保管好 Token，只显示一次

> ⚠️ **安全提醒**：Token 等同于密码，严禁公开分享！

### 3. SSH 密钥（可选，推荐用于频繁操作）

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 复制公钥
cat ~/.ssh/id_ed25519.pub

# 添加到 GitHub: Settings → SSH and GPG keys → New SSH key
```

---

## 🚀 克隆仓库

### 方法一：HTTPS 克隆（推荐新手）

```bash
# 克隆主分支
git clone https://github.com/chenqifu-Ai/openclaw-workspace.git

# 克隆到指定目录
git clone https://github.com/chenqifu-Ai/openclaw-workspace.git my-openclaw

# 克隆特定分支
git clone -b computehub-qwen3.5-397b https://github.com/chenqifu-Ai/openclaw-workspace.git
```

> 首次会提示输入 GitHub 用户名和密码：
> - **用户名**: `chenqifu-Ai`
> - **密码**: 输入你的 **Personal Access Token**

### 方法二：SSH 克隆（推荐频繁使用）

```bash
# 确保 .ssh/config 配置正确
cat ~/.ssh/config

# 克隆
git clone git@github.com:chenqifu-Ai/openclaw-workspace.git
```

### 方法三：Git 大文件（如果仓库很大）

```bash
# 安装 LFS
git lfs install

# 克隆（自动处理 LFS 文件）
git clone --depth 1 https://github.com/chenqifu-Ai/openclaw-workspace.git
```

---

## 🔧 克隆后配置

### 1. 进入目录

```bash
cd openclaw-workspace
```

### 2. 配置 Git 用户信息

```bash
# 查看当前配置
git config --list | grep user

# 设置用户信息（本地仓库专用）
git config user.name "你的GitHub用户名"
git config user.email "你的邮箱@example.com"
```

### 3. 查看分支

```bash
# 查看所有分支
git branch -a

# 切换到主分支
git checkout computehub-qwen3.5-397b

# 查看远程分支
git remote -v
```

### 4. 获取最新代码

```bash
# 拉取最新代码
git pull origin computehub-qwen3.5-397b

# 查看提交历史
git log --oneline -10

# 查看状态
git status
```

---

## 🏗️ OpenClaw 专用配置

### 安装 OpenClaw

```bash
# 检查 OpenClaw 是否已安装
openclaw --version

# 如果没有安装，参考: https://docs.openclaw.ai
npm install -g openclaw
```

### 同步配置

```bash
# 查看工作区结构
ls -la

# 主要目录
# ├── docs/          # 文档
# ├── memory/        # 记忆系统
# ├── skills/        # 技能模块
# ├── SOUL.md        # 人格配置
# ├── AGENTS.md      # 代理规则
# └── HEARTBEAT.md   # 心跳任务
```

### 启动 OpenClaw

```bash
# 启动 Gateway
openclaw gateway start

# 检查状态
openclaw status
```

---

## 📱 多设备同步

### 从一台设备同步到另一台

```bash
# 源设备：推送最新代码
cd openclaw-workspace
git add .
git commit -m "同步更新"
git push origin computehub-qwen3.5-397b

# 目标设备：拉取最新代码
git pull origin computehub-qwen3.5-397b
```

### 处理冲突

```bash
# 如果有冲突，手动解决
git status          # 查看冲突文件
git diff <file>     # 查看差异
git add <file>      # 标记已解决
git commit          # 提交解决
```

---

## 🔒 安全注意事项

### 1. 不要提交敏感信息

```bash
# .gitignore 应包含
.env
*.key
*.pem
*.secret
credentials.json
```

### 2. 定期轮换 Token

```bash
# GitHub: Settings → Developer settings → Personal access tokens
# 删除旧 Token，生成新 Token
# 更新本地配置
git config --global credential.helper store
```

### 3. 分支策略

| 分支 | 用途 | 保护 |
|------|------|------|
| `computehub-qwen3.5-397b` | 主开发分支 | 推送前需审查 |
| `master` | 稳定版本 | 保护分支 |

---

## 🐛 常见问题排查

### 问题 1: 认证失败

```bash
# HTTPS: 清除缓存的凭据
git config --system --unset credential.helper

# 重新克隆，输入 PAT
git clone https://github.com/chenqifu-Ai/openclaw-workspace.git

# 或者使用 SSH
git clone git@github.com:chenqifu-Ai/openclaw-workspace.git
```

### 问题 2: 连接超时

```bash
# 检查网络
ping github.com

# 配置代理（如需）
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy https://proxy.example.com:8080

# 测试 SSH 连接
ssh -T git@github.com
```

### 问题 3: 磁盘空间不足

```bash
# 浅克隆（只拉最新提交）
git clone --depth 1 https://github.com/chenqifu-Ai/openclaw-workspace.git

# 清理 Git 缓存
git gc --aggressive
```

### 问题 4: 权限被拒绝

```bash
# 检查 SSH 权限
ls -la ~/.ssh/
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519

# 测试 SSH 连接
ssh -T -i ~/.ssh/id_ed25519 git@github.com
```

---

## 📊 快速命令参考

```bash
# 克隆
git clone <url>

# 查看状态
git status

# 查看日志
git log --oneline --graph

# 拉取更新
git pull origin <branch>

# 推送更改
git add .
git commit -m "描述"
git push origin <branch>

# 创建新分支
git checkout -b feature-name

# 合并分支
git merge feature-name

# 撤销未提交的更改
git checkout -- .

# 查看远程仓库
git remote -v

# 查看文件大小
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(objectname)' | sort -k2 -n | tail -10
```

---

## 📞 联系方式

| 项目 | 信息 |
|------|------|
| **GitHub** | https://github.com/chenqifu-Ai |
| **仓库** | https://github.com/chenqifu-Ai/openclaw-workspace |
| **文档** | https://docs.openclaw.ai |
| **社区** | https://discord.com/invite/clawd |

---

*文档生成时间: 2026-04-24 22:01*  
*文档版本: v1.0*  
*维护者: 小智 AI 助手*
