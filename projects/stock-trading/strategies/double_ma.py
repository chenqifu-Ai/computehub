# 策略示例 - 双均线策略

## 策略说明

双均线策略是最基础的量化策略之一，利用短期均线上穿长期均线作为买入信号，下穿作为卖出信号。

## 策略代码

```python
def double_ma_strategy(data, short_window=5, long_window=20):
    """
    双均线策略
    
    参数:
        data: 股票数据DataFrame，包含close列
        short_window: 短期均线周期，默认5
        long_window: 长期均线周期，默认20
    
    返回:
        交易信号: 1买入, -1卖出, 0持有
    """
    # 计算均线
    data['short_ma'] = data['close'].rolling(window=short_window).mean()
    data['long_ma'] = data['close'].rolling(window=long_window).mean()
    
    # 生成信号
    data['signal'] = 0
    data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1  # 金叉
    data.loc[data['short_ma'] < data['long_ma'], 'signal'] = -1  # 死叉
    
    # 返回最新信号
    return data['signal'].iloc[-1]


def execute_trade(signal, position, cash, price, max_position=0.8):
    """
    执行交易
    
    参数:
        signal: 交易信号
        position: 当前持仓数量
        cash: 可用现金
        price: 当前价格
        max_position: 最大仓位比例
    
    返回:
        trade_volume: 交易数量（正数买入，负数卖出）
    """
    trade_volume = 0
    
    if signal == 1 and position == 0:
        # 金叉买入
        max_buy = int(cash * max_position / price)
        trade_volume = max_buy
    
    elif signal == -1 and position > 0:
        # 死叉卖出
        trade_volume = -position
    
    return trade_volume


# 回测示例
if __name__ == '__main__':
    import pandas as pd
    
    # 模拟数据
    data = pd.DataFrame({
        'close': [12.0, 12.1, 12.3, 12.2, 12.5, 12.4, 12.35, 
                  12.6, 12.8, 12.7, 12.9, 13.0, 12.8, 12.6]
    })
    
    # 获取信号
    signal = double_ma_strategy(data)
    print(f"当前信号: {signal}")
    
    # 执行交易
    position = 0
    cash = 100000
    price = data['close'].iloc[-1]
    trade_volume = execute_trade(signal, position, cash, price)
    
    if trade_volume > 0:
        print(f"建议买入: {trade_volume}股")
    elif trade_volume < 0:
        print(f"建议卖出: {-trade_volume}股")
    else:
        print("持有不动")
```

## 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| short_window | 5 | 短期均线周期 |
| long_window | 20 | 长期均线周期 |
| max_position | 0.8 | 最大仓位比例 |

## 策略优化方向

1. **均线周期优化**：寻找最优的短期和长期均线组合
2. **止损止盈**：加入止损止盈逻辑
3. **仓位管理**：动态调整仓位
4. **多股票组合**：分散投资降低风险

---

*创建时间：2026-03-21*