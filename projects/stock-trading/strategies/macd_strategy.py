# 策略示例 - MACD策略

## 策略说明

MACD（Moving Average Convergence Divergence）指标是常用的技术分析指标，通过计算快慢两条指数移动平均线的差离值来判断买卖信号。

## 策略代码

```python
def macd_strategy(data, fast_period=12, slow_period=26, signal_period=9):
    """
    MACD策略
    
    参数:
        data: 股票数据DataFrame，包含close列
        fast_period: 快线周期，默认12
        slow_period: 慢线周期，默认26
        signal_period: 信号线周期，默认9
    
    返回:
        交易信号: 1买入, -1卖出, 0持有
    """
    # 计算EMA
    data['ema_fast'] = data['close'].ewm(span=fast_period, adjust=False).mean()
    data['ema_slow'] = data['close'].ewm(span=slow_period, adjust=False).mean()
    
    # 计算MACD
    data['macd'] = data['ema_fast'] - data['ema_slow']
    data['signal'] = data['macd'].ewm(span=signal_period, adjust=False).mean()
    data['histogram'] = data['macd'] - data['signal']
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 金叉买入：MACD上穿信号线
    data.loc[(data['macd'] > data['signal']) & 
             (data['macd'].shift(1) <= data['signal'].shift(1)), 'signal_flag'] = 1
    
    # 死叉卖出：MACD下穿信号线
    data.loc[(data['macd'] < data['signal']) & 
             (data['macd'].shift(1) >= data['signal'].shift(1)), 'signal_flag'] = -1
    
    return data['signal_flag'].iloc[-1]


def enhanced_macd_strategy(data, fast_period=12, slow_period=26, signal_period=9):
    """
    增强版MACD策略（带过滤条件）
    
    过滤条件:
    1. MACD柱状图为正时才买入
    2. MACD柱状图为负时才卖出
    3. 价格在均线上方时优先买入
    """
    # 基础MACD计算
    data['ema_fast'] = data['close'].ewm(span=fast_period, adjust=False).mean()
    data['ema_slow'] = data['close'].ewm(span=slow_period, adjust=False).mean()
    data['macd'] = data['ema_fast'] - data['ema_slow']
    data['signal_line'] = data['macd'].ewm(span=signal_period, adjust=False).mean()
    data['histogram'] = data['macd'] - data['signal_line']
    
    # 辅助指标
    data['ma20'] = data['close'].rolling(window=20).mean()
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 金叉买入（带过滤）
    golden_cross = (data['macd'] > data['signal_line']) & \
                   (data['macd'].shift(1) <= data['signal_line'].shift(1))
    histogram_positive = data['histogram'] > 0
    above_ma = data['close'] > data['ma20']
    
    data.loc[golden_cross & histogram_positive & above_ma, 'signal_flag'] = 1
    
    # 死叉卖出
    death_cross = (data['macd'] < data['signal_line']) & \
                  (data['macd'].shift(1) >= data['signal_line'].shift(1))
    
    data.loc[death_cross, 'signal_flag'] = -1
    
    return data['signal_flag'].iloc[-1]


# 回测示例
if __name__ == '__main__':
    import pandas as pd
    
    # 模拟数据
    data = pd.DataFrame({
        'close': [10.0 + i * 0.1 + (i % 5 - 2) * 0.05 for i in range(100)]
    })
    
    # 获取信号
    signal = macd_strategy(data)
    print(f"MACD信号: {signal}")
    print(f"{'买入' if signal == 1 else '卖出' if signal == -1 else '持有'}")
```

## 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| fast_period | 12 | 快线周期 |
| slow_period | 26 | 慢线周期 |
| signal_period | 9 | 信号线周期 |

## MACD指标解读

### MACD线
- 快线EMA - 慢线EMA
- 反映短期趋势

### 信号线
- MACD线的EMA
- 作为买卖参考线

### 柱状图
- MACD线 - 信号线
- 反映动能强弱

## 买卖信号

### 买入信号（金叉）
1. MACD线上穿信号线
2. 柱状图由负转正
3. 最好在零轴上方

### 卖出信号（死叉）
1. MACD线下穿信号线
2. 柱状图由正转负
3. 最好在零轴下方

## 策略优化方向

1. **添加趋势过滤**：只在趋势方向交易
2. **多周期确认**：多个时间周期信号一致
3. **止损止盈**：设置固定的止损止盈比例
4. **仓位管理**：根据信号强度调整仓位

---

*创建时间：2026-03-21*