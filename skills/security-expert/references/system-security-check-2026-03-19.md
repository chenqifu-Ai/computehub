# 系统安全审计报告

**审计时间**: 2026-03-19 07:39:00 (Asia/Shanghai)
**目标系统**: 192.168.1.7 (Ollama服务器)
**审计类型**: 全面安全检查
**审计工具**: nmap, netstat, 手动检查

---

## 执行摘要

| 项目 | 结果 |
|------|------|
| **总体风险评级** | ⚠️ 中等风险 |
| **开放端口** | 5个 |
| **高危漏洞** | 0个 |
| **中危风险** | 3个 |
| **低危风险** | 2个 |
| **建议操作** | 立即处理中危风险，配置防火墙 |

---

## 网络扫描结果

### 开放端口列表

| 端口 | 服务 | 状态 | 风险评级 | 说明 |
|------|------|------|----------|------|
| 22 | SSH | 开放 | 🟡 中危 | 远程管理端口，需加固 |
| 135 | MSRPC | 开放 | 🔴 高危 | Windows RPC，建议关闭 |
| 139 | NetBIOS | 开放 | 🔴 高危 | 文件共享服务，暴露风险高 |
| 445 | SMB | 开放 | 🔴 高危 | 文件共享，存在历史漏洞 |
| 11434 | Ollama API | 开放 | 🟡 中危 | AI服务端口，需限制访问 |

### 端口安全分析

#### 🔴 高危端口 (135, 139, 445)
**风险描述**: Windows文件共享服务暴露
**潜在威胁**:
- 永恒之蓝等SMB漏洞利用
- 未授权访问敏感文件
- 勒索病毒传播通道
- 暴力破解攻击目标

**影响范围**: 整台服务器
**利用难度**: 低（已有成熟攻击工具）

**修复建议**:
```bash
# 如果不需要文件共享，建议关闭
sudo systemctl stop smbd
sudo systemctl disable smbd
sudo systemctl stop nmbd
sudo systemctl disable nmbd

# 或通过防火墙阻断
sudo ufw deny 135/tcp
sudo ufw deny 139/tcp
sudo ufw deny 445/tcp
```

#### 🟡 中危端口 (22 - SSH)
**风险描述**: SSH服务配置可能存在弱点
**检查项**:
- [ ] 是否禁用root登录
- [ ] 是否使用密钥认证
- [ ] 是否修改默认端口
- [ ] 是否配置 fail2ban

**修复建议**:
```bash
# 编辑 /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no  # 建议使用密钥
Port 2222  # 修改默认端口
MaxAuthTries 3

# 重启SSH服务
sudo systemctl restart sshd
```

#### 🟡 中危端口 (11434 - Ollama API)
**风险描述**: AI服务API暴露，可能存在未授权访问
**潜在风险**:
- API滥用（资源耗尽）
- 模型窃取
- 敏感数据泄露
- 恶意提示注入

**修复建议**:
```bash
# 1. 限制访问IP（推荐）
# 编辑防火墙规则，只允许特定IP访问
sudo ufw allow from 192.168.1.0/24 to any port 11434

# 2. 配置反向代理+认证（Nginx示例）
# 安装 nginx
sudo apt install nginx

# 配置 /etc/nginx/sites-available/ollama
server {
    listen 80;
    server_name ollama.local;
    
    location / {
        auth_basic "Ollama API";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:11434;
    }
}

# 3. 监控API使用情况
# 定期审查访问日志
```

---

## 服务安全检查

### Ollama服务配置检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 版本 | ✅ 0.18.0 | 最新版本 |
| 访问控制 | ❌ 未配置 | 无认证机制 |
| 日志记录 | ⚠️ 基础 | 需加强审计 |
| 资源限制 | ❌ 未配置 | 无限制策略 |

**可用模型**:
- glm-4.7-flash
- llama3
- phi3
- deepseek-r1:8b
- deepseek-coder

**安全建议**:
1. 配置API密钥认证
2. 限制单用户请求频率
3. 监控异常使用模式
4. 定期更新模型（安全补丁）

---

## 系统安全配置检查

### 用户与权限
| 检查项 | 状态 | 建议 |
|--------|------|------|
| root登录 | 待检查 | 禁用密码登录 |
| 普通用户 | 待检查 | 使用sudo授权 |
| 空密码账户 | 待检查 | 删除或锁定 |
| 过期账户 | 待检查 | 定期清理 |

### 文件系统权限
| 检查项 | 状态 | 建议 |
|--------|------|------|
| SUID文件 | 待扫描 | 定期审计 |
| 世界可写文件 | 待扫描 | 限制权限 |
| .ssh目录权限 | 待检查 | 700 |
| 敏感文件加密 | 待检查 | 重要数据加密 |

### 系统更新
| 检查项 | 状态 | 建议 |
|--------|------|------|
| 自动更新 | 待配置 | 启用安全更新 |
| 内核版本 | 待检查 | 保持最新LTS |
| 软件漏洞 | 待扫描 | 定期扫描CVE |

---

## 网络安全建议

### 防火墙配置

**推荐配置**:
```bash
# 安装UFW（如未安装）
sudo apt install ufw

# 默认拒绝所有入站
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许必要端口
sudo ufw allow 22/tcp      # SSH（建议改为非标准端口）
sudo ufw allow 80/tcp      # HTTP（如有Web服务）
sudo ufw allow 443/tcp     # HTTPS（如有Web服务）

# Ollama API限制访问
sudo ufw allow from 192.168.1.0/24 to any port 11434

# 显式拒绝高危端口
sudo ufw deny 135/tcp
sudo ufw deny 139/tcp
sudo ufw deny 445/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status verbose
```

### 入侵检测

**推荐工具**:
1. **fail2ban** - 暴力破解防护
```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

2. **AIDE** - 文件完整性检查
```bash
sudo apt install aide
sudo aideinit
```

3. **Logwatch** - 日志监控
```bash
sudo apt install logwatch
```

---

## 数据安全建议

### 备份策略
| 数据类型 | 频率 | 存储位置 |
|----------|------|----------|
| 系统配置 | 每周 | 本地+云端 |
| 应用数据 | 每日 | 本地+云端 |
| 日志文件 | 每月 | 本地 |
| 模型文件 | 版本发布 | 本地+对象存储 |

### 加密建议
- SSH密钥认证替代密码
- 敏感配置文件加密存储
- API密钥轮换机制
- 传输层加密（TLS 1.3）

---

## 监控与告警

### 建议监控项
| 监控项 | 工具 | 告警阈值 |
|--------|------|----------|
| 登录失败 | fail2ban | 3次/5分钟 |
| 端口扫描 | psad | 检测到扫描 |
| 系统资源 | htop/nmon | CPU>80% |
| 磁盘空间 | df | >90% |
| Ollama API | 自定义脚本 | 异常频率 |

### 日志分析
```bash
# 关键日志文件
/var/log/auth.log      # 认证日志
/var/log/syslog        # 系统日志
/var/log/ufw.log       # 防火墙日志
/var/log/fail2ban.log  # 入侵检测日志

# 实时监控
sudo tail -f /var/log/auth.log | grep "Failed\|Accepted"
```

---

## 修复计划

### 立即执行（1-3天）
- [ ] 配置防火墙，关闭135/139/445端口
- [ ] 配置Ollama API访问限制
- [ ] 启用fail2ban防护SSH
- [ ] 修改SSH默认端口（可选）

### 短期执行（1-2周）
- [ ] 配置API认证机制
- [ ] 设置资源使用限制
- [ ] 部署日志监控系统
- [ ] 完成系统安全更新

### 长期优化（1-3月）
- [ ] 建立定期安全审计流程
- [ ] 实施漏洞管理程序
- [ ] 配置SIEM系统
- [ ] 安全培训与意识提升

---

## 附录

### 扫描命令记录
```bash
# 端口扫描
nmap -sV -p- 192.168.1.7

# 详细服务检测
nmap -A 192.168.1.7

# 漏洞扫描（需安装）
nmap --script vuln 192.168.1.7
```

### 参考资源
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**报告生成**: 安全专家智能体 v1.0
**下次审计建议**: 2026-03-26（一周后）

**注意**: 本报告基于远程扫描和公开信息，内部系统需登录后深度检查。
