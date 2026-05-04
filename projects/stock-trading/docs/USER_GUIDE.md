# 股票交易软件 - 使用指南

## 一、快速开始

### 1. 登录

- 用户名：`admin`
- 密码：`admin123`
- 初始资金：`1,000,000元`

### 2. 首页

登录后进入主页，可以看到：
- 账户总览（资金/持仓/盈亏）
- 自选股票行情
- 策略列表
- 最新交易记录

## 二、行情功能

### 1. 搜索股票

在搜索框输入股票代码或名称：
- 支持模糊搜索
- 显示匹配结果列表

### 2. 查看行情

点击股票查看：
- 实时价格
- 涨跌幅
- 成交量
- 历史K线图

### 3. K线图

支持三种周期：
- 日线
- 周线
- 月线

## 三、策略功能

### 1. 创建策略

点击"新建策略"，填写：
- 策略名称
- 策略描述
- 策略代码（Python）

### 2. 策略模板

#### 双均线策略

```python
def strategy(df):
    df['short_ma'] = df['close'].rolling(5).mean()
    df['long_ma'] = df['close'].rolling(20).mean()
    df['signal'] = 0
    df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
    df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1
    return df['signal']
```

#### MACD策略

```python
def strategy(df):
    df['ema12'] = df['close'].ewm(span=12).mean()
    df['ema26'] = df['close'].ewm(span=26).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal_line'] = df['macd'].ewm(span=9).mean()
    df['signal'] = 0
    df.loc[df['macd'] > df['signal_line'], 'signal'] = 1
    df.loc[df['macd'] < df['signal_line'], 'signal'] = -1
    return df['signal']
```

### 3. 策略信号说明

| 信号值 | 含义 |
|--------|------|
| 1 | 买入信号 |
| -1 | 卖出信号 |
| 0 | 持有/观望 |

### 4. 回测策略

选择策略后点击"回测"：
1. 选择股票
2. 选择时间范围
3. 设置初始资金
4. 查看回测结果

### 5. 回测指标说明

| 指标 | 说明 |
|------|------|
| 总收益率 | 整个回测期间的收益百分比 |
| 年化收益率 | 按年计算的收益率 |
| 最大回撤 | 从最高点到最低点的最大跌幅 |
| 夏普比率 | 风险调整后收益，越高越好 |
| 胜率 | 盈利交易占总交易的比例 |

## 四、交易功能

### 1. 买入股票

1. 输入股票代码
2. 选择买入价格（默认实时价）
3. 输入买入数量
4. 确认交易

### 2. 卖出股票

1. 选择持仓中的股票
2. 输入卖出数量
3. 确认交易

### 3. 查看持仓

持仓页面显示：
- 股票代码/名称
- 持仓数量
- 成本价
- 当前价
- 盈亏
- 盈亏比例

## 五、账户功能

### 1. 账户总览

- 可用资金
- 冻结资金
- 持仓市值
- 总资产
- 总盈亏

### 2. 交易记录

查看所有交易历史：
- 交易时间
- 股票
- 交易类型（买入/卖出）
- 数量/金额

## 六、API使用

### 认证

```bash
# 注册
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 行情

```bash
# 获取股票列表
curl http://localhost:8000/api/v1/market/stocks

# 获取实时行情
curl http://localhost:8000/api/v1/market/quote/000001

# 获取K线
curl "http://localhost:8000/api/v1/market/kline/000001?start=2024-01-01&end=2024-12-31"
```

### 交易

```bash
# 获取持仓
curl http://localhost:8000/api/v1/trading/positions \
  -H "Authorization: Bearer <token>"

# 买入
curl -X POST http://localhost:8000/api/v1/trading/order \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001","order_type":"buy","volume":100}'
```

---

*最后更新：2026-03-21*