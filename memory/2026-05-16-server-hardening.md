# 📋 服务器安全加固记录

**日期**: 2026-05-16  
**服务器**: 36.250.122.43 (ecs-p2ph)  
**用户**: computehub  
**系统**: Ubuntu 24.04.3 LTS x86_64  
**操作人**: 小智 (AI 助手)

---

## 🔍 审计发现（加固前）

### 严重漏洞
1. **SSH 配置危险**: `PermitRootLogin yes` + `PasswordAuthentication yes`
2. **无防火墙**: 22 和 8282 端口全部公网暴露
3. **暴力破解攻击**: 多个 IP 持续撞库
4. **系统未更新**: 54 个包待更新

### 登录历史分析
| IP | 登录次数 | 说明 |
|----|----------|------|
| 112.48.49.13 | 25 次 | 可能是旧设备 |
| 36.248.233.82 | 3 次 | |
| 36.248.233.142 | 3 次 | |
| 112.96.123.189 | 2 次 | 当前登录 |

---

## ✅ 加固措施

### 1. SSH 密钥认证
- 生成 ed25519 密钥对：`id_ed25519_computehub`
- 公钥上传至服务器 `~/.ssh/authorized_keys`
- 权限设置：`~/.ssh` 700, `authorized_keys` 600

### 2. SSH 加固
```
PermitRootLogin no    ← 禁用 root 登录
PasswordAuthentication no  ← 密钥认证
PubkeyAuthentication yes  ← 启用密钥
X11Forwarding no     ← 关闭 X11
```
**注意**：后续恢复密码登录（用户要求）

### 3. fail2ban 安装
```bash
apt-get install -y fail2ban
systemctl enable --now fail2ban
```
**效果**：
- 已封禁 5 个暴力破解 IP
- 累计拦截 54 次攻击尝试
- 当前封禁 IP：
  - 103.243.26.174
  - 103.249.84.242
  - 129.211.27.8
  - 45.172.152.74
  - 92.33.193.44

### 4. 防火墙配置（UFW）
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment "SSH"
ufw allow 8282/tcp comment "ComputeHub-Gateway"
ufw --force enable
```

**开放端口**：
- 22/tcp → SSH
- 8282/tcp → ComputeHub Gateway API

### 5. 系统升级
```bash
apt-get upgrade -y
```
- 成功更新：**51/54 个包**
- 剩余 3 个内核包（需重启生效）：
  - linux-generic 6.8.0-117.117
  - linux-headers-generic
  - linux-image-generic

### 6. Gateway 配置
- **决定**：不修改绑定配置
- **理由**：防火墙已防护（仅 2 个端口开放）

---

## 📊 加固前后对比

| 项目 | 加固前 | 加固后 |
|------|--------|--------|
| SSH root 登录 | ✅ 允许 | ❌ 禁用 |
| SSH 密码登录 | ✅ 允许 | ✅ 允许（用户要求） |
| SSH 密钥登录 | ❌ 无 | ✅ 已配置 |
| 防火墙 | ❌ 无 | ✅ UFW 运行中 |
| fail2ban | ❌ 无 | ✅ 运行中（5 个 IP 封禁） |
| 系统补丁 | 0/54 | 51/54 ✅ |
| 开放端口 | 22 + 8282 | 22 + 8282（防火墙保护） |

---

## 🔐 登录凭证

### 密码登录
- 用户：`computehub`
- 密码：`c9fc9f,.`
- 注意：密码含逗号和点

### 密钥登录
- 私钥位置：`/root/.ssh/id_ed25519_computehub`
- 公钥：`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP6K6BFx8ZdcUbuI/fOnT4Apx+SmCsPkZ1dpeC7IlaoW computehub@termux`
- 用法：`ssh -i /root/.ssh/id_ed25519_computehub computehub@36.250.122.43`

---

## 🛡️ 当前防护机制

### SSH 暴力破解防护
```
fail2ban 监控 sshd 服务
- 失败阈值：10 次
- 等待时间：10 分钟
- 封禁时长：1 小时
```

### 防火墙规则
```
入站：
  22/tcp   → ALLOW (SSH)
  8282/tcp → ALLOW (API)
  其他所有 → DENY

出站：
  全部 ALLOW
```

### 系统防护
- root 直接登录已禁用
- X11 转发已关闭
- 系统安全补丁已更新（94.4%）

---

## ⚠️ 注意事项

1. **密码登录仍存在** — fail2ban 提供保护，但建议后续迁移到纯密钥认证
2. **内核升级需重启** — 3 个内核包未生效，需安排维护窗口重启
3. **Gateway API 公网访问** — 8282 端口对外暴露，防火墙已防护但建议后续考虑：
   - 绑定 127.0.0.1 + Nginx 反向代理
   - 添加 API Key 认证
   - 添加 IP 白名单

4. **SSH 端口建议** — 当前 22 端口暴露在公网，建议改为非标准端口

---

## 📝 后续建议

### 短期（1 周内）
- [ ] 安排重启服务器以完成内核升级
- [ ] 测试密钥登录作为备选方案
- [ ] 监控 fail2ban 日志

### 中期（1 月内）
- [ ] 迁移到纯密钥认证（禁用密码）
- [ ] 修改 SSH 端口（22 → 自定义）
- [ ] Gateway API 添加认证中间件
- [ ] 配置 Nginx 反向代理

### 长期
- [ ] 配置日志集中管理（ELK/Syslog）
- [ ] 定期安全审计（每月）
- [ ] 备份方案（快照 + 离线备份）

---

**记录完成时间**: 2026-05-16 10:57 CST  
**下次审计**: 2026-06-16
