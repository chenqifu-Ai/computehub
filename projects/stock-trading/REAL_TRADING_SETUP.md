# 实盘交易配置指南

## 当前状态

### ✅ 已完成
1. **模拟券商** - 完全可用，用于测试
2. **券商接口框架** - 支持多券商切换
3. **实盘接口模板** - 东方财富、华泰证券、讯投 QMT

### 📝 待配置
1. **券商账号** - 需要配置真实券商账号
2. **依赖安装** - 安装对应券商的 Python 库
3. **实盘测试** - 小额资金测试

---

## 支持的券商

### 1. 东方财富 (推荐)

**特点**: 
- 接口成熟稳定
- 支持股票、基金、债券
- 有免费 Python 库 `efinance`

**安装依赖**:
```bash
pip install efinance
```

**配置步骤**:
1. 编辑配置文件: `backend/config/brokers/default.json`
2. 修改 `eastmoney` 配置:
```json
{
    "eastmoney": {
        "name": "东方财富",
        "type": "eastmoney",
        "enabled": true,
        "config": {
            "account": "你的东方财富账号",
            "password": "你的交易密码",
            "trade_server": "https://trade.eastmoney.com",
            "hq_server": "https://hq.eastmoney.com"
        }
    }
}
```
3. 重启服务

**测试命令**:
```bash
# 查询账户
curl http://localhost:8000/api/broker/account

# 查询持仓
curl http://localhost:8000/api/broker/positions

# 买入测试（100 股）
curl -X POST http://localhost:8000/api/broker/order \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001","direction":"buy","volume":100,"price":10.5}'
```

---

### 2. 华泰证券

**特点**:
- 大券商，稳定可靠
- 需要开通程序化交易权限
- 使用 `htsc` 专用接口

**配置步骤**:
1. 联系华泰证券开通程序化交易权限
2. 获取交易客户端路径
3. 编辑配置文件:
```json
{
    "htsc": {
        "name": "华泰证券",
        "type": "htsc",
        "enabled": true,
        "config": {
            "account": "你的华泰账号",
            "password": "你的交易密码",
            "client_path": "C:\\htsc\\client.exe"
        }
    }
}
```

---

### 3. 讯投 QMT (专业版)

**特点**:
- 专业量化交易平台
- 支持复杂策略
- 需要付费购买

**安装依赖**:
```bash
pip install xtquant
```

**配置**:
```json
{
    "xtquant": {
        "name": "讯投 QMT",
        "type": "xtquant",
        "enabled": true,
        "config": {
            "account": "你的 QMT 账号",
            "password": "你的密码",
            "qmt_path": "C:\\QMT\\client.exe"
        }
    }
}
```

---

## 快速切换券商

```bash
# 查看当前券商
curl http://localhost:8000/api/broker/current

# 切换到东方财富
curl -X POST http://localhost:8000/api/broker/switch \
  -H "Content-Type: application/json" \
  -d '{"broker_id":"eastmoney"}'

# 切换回模拟交易
curl -X POST http://localhost:8000/api/broker/switch \
  -H "Content-Type: application/json" \
  -d '{"broker_id":"simulator"}'
```

---

## 实盘交易流程

### 1. 准备工作
- [ ] 选择券商并开通权限
- [ ] 安装对应 Python 库
- [ ] 配置账号信息
- [ ] 小额资金测试

### 2. 测试步骤
1. **查询账户** - 确认资金余额
2. **查询持仓** - 确认当前持仓
3. **小额买入** - 买入 100 股测试
4. **查询成交** - 确认订单状态
5. **卖出平仓** - 卖出测试
6. **确认结果** - 检查资金变化

### 3. 风险控制
- ⚠️ **首次实盘**: 建议不超过 1 万元
- ⚠️ **单笔交易**: 不超过总资金 10%
- ⚠️ **止损设置**: 提前设置止损点
- ⚠️ **监控日志**: 实时查看交易日志

---

## API 端点参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/broker/list` | GET | 列出所有券商 |
| `/api/broker/current` | GET | 当前券商 |
| `/api/broker/switch` | POST | 切换券商 |
| `/api/broker/account` | GET | 账户信息 |
| `/api/broker/positions` | GET | 持仓列表 |
| `/api/broker/orders` | GET | 订单列表 |
| `/api/broker/order` | POST | 下单 |
| `/api/broker/cancel` | POST | 撤单 |
| `/api/broker/quote/{code}` | GET | 实时行情 |

---

## 日志查看

```bash
# 实时查看交易日志
tail -f /tmp/stock-server.log

# 查看最近 100 行
tail -100 /tmp/stock-server.log
```

---

## 常见问题

### Q1: 登录失败？
- 检查账号密码是否正确
- 确认券商服务是否正常
- 查看日志文件错误信息

### Q2: 下单失败？
- 检查资金是否充足
- 确认股票是否停牌
- 检查价格是否在涨跌停范围内

### Q3: 持仓查询为空？
- 确认是否有持仓
- 检查券商配置是否正确
- 确认券商接口是否支持该功能

---

**下一步**: 选择一家券商，配置账号，开始实盘测试！
