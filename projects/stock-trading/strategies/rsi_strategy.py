# 策略示例 - RSI策略

## 策略说明

RSI（Relative Strength Index，相对强弱指标）是衡量价格变动速度和变化的技术指标，取值范围0-100，通常用于判断超买超卖。

## 策略代码

```python
def rsi_strategy(data, period=14, oversold=30, overbought=70):
    """
    RSI策略
    
    参数:
        data: 股票数据DataFrame，包含close列
        period: RSI周期，默认14
        oversold: 超卖线，默认30
        overbought: 超买线，默认70
    
    返回:
        交易信号: 1买入, -1卖出, 0持有
    """
    # 计算价格变化
    delta = data['close'].diff()
    
    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 计算平均上涨和下跌
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 计算RS和RSI
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 超卖买入：RSI从下往上穿过超卖线
    data.loc[(data['rsi'] > oversold) & 
             (data['rsi'].shift(1) <= oversold), 'signal_flag'] = 1
    
    # 超买卖出：RSI从上往下穿过超买线
    data.loc[(data['rsi'] < overbought) & 
             (data['rsi'].shift(1) >= overbought), 'signal_flag'] = -1
    
    return data['rsi'].iloc[-1], data['signal_flag'].iloc[-1]


def enhanced_rsi_strategy(data, period=14, oversold=30, overbought=70):
    """
    增强版RSI策略（带背离检测）
    
    背离信号:
    - 底背离：价格创新低但RSI未创新低 → 可能反转上涨
    - 顶背离：价格创新高但RSI未创新高 → 可能反转下跌
    """
    # 基础RSI计算
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # 检测背离
    data['price_low'] = data['close'].rolling(window=20).min()
    data['price_high'] = data['close'].rolling(window=20).max()
    data['rsi_low'] = data['rsi'].rolling(window=20).min()
    data['rsi_high'] = data['rsi'].rolling(window=20).max()
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 超卖买入
    oversold_signal = (data['rsi'] > oversold) & (data['rsi'].shift(1) <= oversold)
    data.loc[oversold_signal, 'signal_flag'] = 1
    
    # 底背离买入（更强的信号）
    bottom_divergence = (data['close'] == data['price_low']) & \
                         (data['rsi'] > data['rsi'].shift(5))
    data.loc[bottom_divergence & (data['rsi'] < 50), 'signal_flag'] = 1
    
    # 超买卖出
    overbought_signal = (data['rsi'] < overbought) & (data['rsi'].shift(1) >= overbought)
    data.loc[overbought_signal, 'signal_flag'] = -1
    
    # 顶背离卖出（更强的信号）
    top_divergence = (data['close'] == data['price_high']) & \
                      (data['rsi'] < data['rsi'].shift(5))
    data.loc[top_divergence & (data['rsi'] > 50), 'signal_flag'] = -1
    
    return data['rsi'].iloc[-1], data['signal_flag'].iloc[-1]


# 使用示例
if __name__ == '__main__':
    import pandas as pd
    
    # 模拟数据
    data = pd.DataFrame({
        'close': [10.0 + (i % 10) * 0.5 - 2.5 for i in range(100)]
    })
    
    # 获取信号
    rsi, signal = rsi_strategy(data)
    print(f"RSI值: {rsi:.2f}")
    print(f"信号: {signal}")
    print(f"{'买入' if signal == 1 else '卖出' if signal == -1 else '持有'}")
```

## 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| period | 14 | RSI计算周期 |
| oversold | 30 | 超卖线 |
| overbought | 70 | 超买线 |

## RSI指标解读

### 超买区（>70）
- 价格可能过高
- 考虑卖出

### 超卖区（<30）
- 价格可能过低
- 考虑买入

### 中间区域（30-70）
- 正常波动区间
- 观望为主

## 买卖信号

### 买入信号
1. RSI从超卖区向上突破30
2. 底背离：价格新低，RSI未新低
3. RSI在超卖区形成双底

### 卖出信号
1. RSI从超买区向下跌破70
2. 顶背离：价格新高，RSI未新高
3. RSI在超买区形成双顶

## 策略优化方向

1. **结合趋势**：只在趋势方向交易
2. **多指标确认**：结合MACD、均线等
3. **动态区间**：根据波动率调整超买超卖线
4. **背离过滤**：只在背离时交易

---

*创建时间：2026-03-21*