# 🛡️ ECS 服务器 SSH 连接故障排查经验

**日期**: 2026-05-17
**服务器**: 36.250.122.43 (ecs-p2ph)
**操作系统**: Ubuntu 24.04 LTS (云服务器 ECS)

---

## 一、问题现象

SSH 连接 `computehub@36.250.122.43` 超时：

```
ssh: connect to host 36.250.122.43 port 22: Connection timed out
```

同时 `ping`、`curl` 网关端口也全部不通，看起来像整机失联。

## 二、排查过程

### Step 1: 检查 fail2ban

```bash
fail2ban-client status sshd
```

输出：

```
Currently banned: 8
Banned IP list: 115.140.161.61 193.46.255.86 ... (全是外国IP)
```

**结论**: 你的 IP 不在封禁列表。误以为被 fail2ban 封了，实际不是。

### Step 2: 检查 SSHD 状态

通过云厂商 Web Console/VNC 进入服务器：

```bash
systemctl status sshd  → active (running) ✅
ss -tlnp | grep :22    → 0.0.0.0:22 LISTEN ✅
```

**结论**: SSHD 正常运行，端口在监听。问题不在 SSHD 本身。

### Step 3: 检查 iptables — 找到真凶

```bash
iptables -L -n
```

```
Chain INPUT (policy DROP)    ← 默认策略是 DROP！所有入站拦截！
```

再详细看：

```
num  target  prot  source    destination
1    ACCEPT  tcp  0.0.0.0/0 0.0.0.0/0   tcp dpt:22
2    ACCEPT  0    0.0.0.0/0 0.0.0.0/0   state RELATED,ESTABLISHED
3    ufw-before-logging-input ...
...
```

之前有规则但在重启后丢失了（或者是服务器初始化时没配完整），实际上只有 UFW 的规则在工作，而 UFW 的 SSH 规则在 iptables 层没有优先权。

### Step 4: 添加 iptables 规则修复连接

```bash
iptables -I INPUT 1 -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT
```

**立刻生效** → SSH 可以连接了，但认证失败。

### Step 5: SSH 密钥认证修复

连接通了但报 `Permission denied (publickey,password)`。

检查 `~/.ssh/authorized_keys`，发现缺少对应的 Ed25519 公钥。

**修复**: 将本地公钥追加到 `authorized_keys`：

```bash
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBU3vD0gwjXN9pFdzrtwCMRHHfaNxeQ6Yl21Ii1lfHhZ' >> /home/computehub/.ssh/authorized_keys
chown computehub:computehub /home/computehub/.ssh/authorized_keys
chmod 600 /home/computehub/.ssh/authorized_keys
```

### Step 6: 持久化 iptables 规则

```bash
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
```

---

## 三、故障链路总结

```
用户报告SSH超时
  ↓
❌ 排查 fail2ban → IP 未被封（外国IP被封了，但无关）
  ↓
❌ 排查 SSHD 进程 → 正常运行
  ↓
❌ 排查 SSHD 端口 → 正常监听
  ↓
✅ 排查 iptables → INPUT 策略 DROP（真凶）
  ↓
✅ 添加允许规则 → SSH 连接恢复
  ↓
✅ 添加 SSH 公钥 → 密钥认证恢复
```

## 四、核心教训 🔥

### 1. iptables INPUT 默认策略是 DROP — 要检查

云服务器初始化后，`iptables` 可能配置了 `INPUT policy DROP`，但没有放行 SSH。即使 UFW 显示放行了，底层 iptables 规则可能不一致。

**排查优先级**: SSHD 在跑 → 端口在监听 → **iptables 规则** → fail2ban

不要被 fail2ban 的外国 IP 封禁列表分散注意力。

### 2. SSH 连不上可能有多层问题叠加

这次其实是**两层问题**叠加：
- 第一层: iptables 拦了入站（导致超时）
- 第二层: 公钥没配（导致认证失败）

修复第一层后暴露了第二层问题。**逐步排除，不要在一个问题上死磕。**

### 3. SSH 密钥配置检查清单

| 检查项 | 命令 |
|--------|------|
| 是否生成密钥 | `ls ~/.ssh/id_ed25519.pub` |
| 是否在 authorized_keys | `cat ~/.ssh/authorized_keys \| grep <你的公钥>` |
| 权限正确 | `chmod 600 ~/.ssh/authorized_keys` |
| 所属用户正确 | `chown computehub:computehub ~/.ssh/authorized_keys` |

### 4. 云服务器 iptables 持久化

Ubuntu 默认不带 `iptables-persistent`，重启后 iptables 规则丢失。需要手动保存：

```bash
# 方法 A: iptables-persistent
apt install iptables-persistent
netfilter-persistent save

# 方法 B: 手动保存（最小依赖）
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
```

### 5. fail2ban 调优（减少误伤）

```bash
# bantime 从默认 10m 或更久缩短到 5min
fail2ban-client set sshd bantime 300

# 加白名单自己的 IP
fail2ban-client set sshd addignoreip 112.48.49.13
```

### 6. SSH 连接复用（减少触发 fail2ban）

```bash
# ~/.ssh/config
Host 36.250.122.43
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m
```

多个 SSH 命令共用一个 TCP 连接，不会触发 fail2ban 的 maxretry 阈值。

---

## 五、最佳排查顺序

```
SSH 连不上
  ├── 能否通过 VNC/Console 进服务器？
  │   ├── 否 → 联系云厂商 / 看机房
  │   └── 是 → 继续排查
  │
  ├── systemctl status sshd      → 进程在不在
  ├── ss -tlnp | grep :22        → 端口在不在
  ├── iptables -L -n | grep DROP → 防火墙拦没拦  ← 最容易忽略！
  ├── fail2ban-client status sshd → 被封了没
  └── tail -f /var/log/auth.log  → 看日志
```

## 六、相关命令速查

| 命令 | 用途 |
|------|------|
| `iptables -L -n` | 查看 iptables 规则 |
| `iptables -L -n --line-numbers` | 带行号查看 |
| `iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT` | 插入 SSH 放行规则 |
| `iptables-save > /etc/iptables/rules.v4` | 持久化规则 |
| `fail2ban-client status sshd` | 查看被封 IP |
| `fail2ban-client set sshd unbanip <IP>` | 解封 |
| `fail2ban-client set sshd bantime <秒>` | 调整封禁时长 |
| `fail2ban-client set sshd addignoreip <IP>` | 添加白名单 |
| `ufw status` | 查看 UFW 状态 |
| `ss -tlnp` | 监听端口 |

---

*创建: 2026-05-17 | 关联事件: computehub@ecs-p2ph SSH 失联恢复全流程*
