# Knowledge: ECS服务器SSH连接故障排查流程
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: SSH, ECS, 故障排查, iptables, 安全组, 网络安全
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 问题现象
SSH连接ECS超时，ping/curl全部不通

## 排查顺序
1. 检查fail2ban — fail2ban-client status sshd（看是否被封）
2. 检查SSHD状态 — systemctl status sshd（确认服务运行）
3. 检查iptables — iptables -L -n（找到真凶！）
4. 检查安全组 — 阿里云控制台安全组规则

## 真凶：iptables INPUT 默认策略 DROP
Chain INPUT (policy DROP)
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -P INPUT ACCEPT

## 预防措施
- 定期检查iptables规则
- 配置iptables规则持久化（iptables-persistent）
- 安全组和iptables双重检查

完整文档: memory/topics/部署运维/ECS服务器SSH连接故障排查经验.md
