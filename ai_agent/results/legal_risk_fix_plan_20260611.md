# 🔒 法律风险修复计划

## 📋 风险评估结果
**评估时间**: 2026-06-11 12:03  
**风险等级**: LOW (低风险)
**发现问题**: 4个

---

## 🚨 发现的安全风险

### 1. ⚠️ 知识产权保护问题 (3个)

**问题文件**: 
- `scripts/ollama_router.py` - 疑似硬编码密钥
- `scripts/ssh_diagnose.py` - 疑似硬编码密钥  
- `scripts/video_frame_analysis.py` - 疑似硬编码密钥

**修复方案**:
```bash
# 1. 检查并移除硬编码密钥
sed -i '/api_key.*=.*"/d' scripts/ollama_router.py
sed -i '/password.*=.*"/d' scripts/ssh_diagnose.py
sed -i '/token.*=.*"/d' scripts/video_frame_analysis.py

# 2. 改用环境变量或配置文件
export OLLAMA_API_KEY="your_key"
export SSH_PASSWORD="your_password" 
export VIDEO_API_TOKEN="your_token"
```

### 2. ⚠️ 税务合规问题 (1个)

**问题**: 税务目录不存在

**修复方案**:
```bash
# 创建税务管理目录
mkdir -p /root/.openclaw/workspace/finance/taxes/

# 创建基础税务文件
touch /root/.openclaw/workspace/finance/taxes/2026_q2.md
touch /root/.openclaw/workspace/finance/taxes/records.csv
```

---

## 🗓️ 修复时间表

### 立即处理 (今天完成)
- [ ] 检查并移除硬编码密钥
- [ ] 创建税务管理目录结构

### 短期计划 (本周完成)  
- [ ] 配置环境变量管理敏感信息
- [ ] 建立密钥轮换机制
- [ ] 编写税务记录模板

### 长期计划 (本月完成)
- [ ] 实施完整的密钥管理系统
- [ ] 建立定期安全审计流程
- [ ] 配置自动化税务记录

---

## 🛡️ 预防措施

### 代码审查规则
```markdown
1. ❌ 禁止硬编码密钥、密码、token
2. ✅ 必须使用环境变量或配置中心
3. ✅ 敏感信息必须加密存储
4. ✅ 定期进行安全扫描
```

### 开发规范
```bash
# 使用环境变量示例
export API_KEY=$(cat /path/to/secure/key)
python script.py

# 使用配置文件示例  
{
  "api_key": "从安全存储获取",
  "db_password": "加密存储"
}
```

---

## 📊 风险等级变化

| 时间 | 风险等级 | 问题数量 | 状态 |
|------|----------|----------|------|
| 评估前 | ❓ 未知 | - | 未评估 |
| 2026-06-11 | 🟡 LOW | 4 | 已识别 |
| 修复后目标 | 🟢 VERY LOW | 0 | 目标 |

---

**修复计划制定**: 2026-06-11 12:05  
**负责人**: 法务顾问 + 技术团队
**下次评估**: 2026-07-11 (30天后)