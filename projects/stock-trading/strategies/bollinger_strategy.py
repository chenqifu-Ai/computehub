# 策略示例 - 布林带策略

## 策略说明

布林带（Bollinger Bands）是由约翰·布林格开发的技术分析工具，由三条轨道组成：中轨（移动平均线）、上轨（中轨+2倍标准差）、下轨（中轨-2倍标准差）。

## 策略代码

```python
def bollinger_strategy(data, period=20, std_dev=2):
    """
    布林带策略
    
    参数:
        data: 股票数据DataFrame，包含close列
        period: 移动平均周期，默认20
        std_dev: 标准差倍数，默认2
    
    返回:
        交易信号: 1买入, -1卖出, 0持有
    """
    # 计算中轨（移动平均）
    data['middle_band'] = data['close'].rolling(window=period).mean()
    
    # 计算标准差
    data['std'] = data['close'].rolling(window=period).std()
    
    # 计算上轨和下轨
    data['upper_band'] = data['middle_band'] + std_dev * data['std']
    data['lower_band'] = data['middle_band'] - std_dev * data['std']
    
    # 计算带宽（Bandwidth）
    data['bandwidth'] = (data['upper_band'] - data['lower_band']) / data['middle_band']
    
    # 计算%B（价格在布林带中的位置）
    data['percent_b'] = (data['close'] - data['lower_band']) / \
                         (data['upper_band'] - data['lower_band'])
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 下轨买入：价格触及下轨
    touch_lower = (data['close'] <= data['lower_band'])
    data.loc[touch_lower & (data['close'].shift(1) > data['lower_band'].shift(1)), 'signal_flag'] = 1
    
    # 上轨卖出：价格触及上轨
    touch_upper = (data['close'] >= data['upper_band'])
    data.loc[touch_upper & (data['close'].shift(1) < data['upper_band'].shift(1)), 'signal_flag'] = -1
    
    # 中轨支撑买入
    data.loc[(data['close'] > data['middle_band']) & 
             (data['close'].shift(1) <= data['middle_band'].shift(1)), 'signal_flag'] = 1
    
    return data['signal_flag'].iloc[-1]


def bollinger_squeeze_strategy(data, period=20, std_dev=2):
    """
    布林带收窄突破策略
    
    原理：
    - 布林带收窄表示波动率降低
    - 收窄后往往会有突破行情
    - 配合成交量确认突破方向
    """
    # 基础布林带计算
    data['middle_band'] = data['close'].rolling(window=period).mean()
    data['std'] = data['close'].rolling(window=period).std()
    data['upper_band'] = data['middle_band'] + std_dev * data['std']
    data['lower_band'] = data['middle_band'] - std_dev * data['std']
    data['bandwidth'] = (data['upper_band'] - data['lower_band']) / data['middle_band']
    
    # 计算带宽历史分位数
    data['bandwidth_rank'] = data['bandwidth'].rolling(window=100).rank(pct=True)
    
    # 收窄定义：带宽在历史最低20%区间
    data['is_squeeze'] = data['bandwidth_rank'] < 0.2
    
    # 生成信号
    data['signal_flag'] = 0
    
    # 收窄后向上突破
    breakout_up = data['is_squeeze'].shift(1) & \
                  (data['close'] > data['upper_band'])
    data.loc[breakout_up, 'signal_flag'] = 1
    
    # 收窄后向下突破
    breakout_down = data['is_squeeze'].shift(1) & \
                    (data['close'] < data['lower_band'])
    data.loc[breakout_down, 'signal_flag'] = -1
    
    return data['signal_flag'].iloc[-1]


# 使用示例
if __name__ == '__main__':
    import pandas as pd
    
    # 模拟数据
    data = pd.DataFrame({
        'close': [10.0 + i * 0.1 + (i % 5 - 2) * 0.2 for i in range(100)]
    })
    
    # 获取信号
    signal = bollinger_strategy(data)
    print(f"布林带信号: {signal}")
    print(f"{'买入' if signal == 1 else '卖出' if signal == -1 else '持有'}")
```

## 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| period | 20 | 移动平均周期 |
| std_dev | 2 | 标准差倍数 |

## 布林带指标解读

### 上轨
- 中轨 + 2倍标准差
- 价格压力位

### 中轨
- N日移动平均
- 价格中枢

### 下轨
- 中轨 - 2倍标准差
- 价格支撑位

### 带宽
- (上轨 - 下轨) / 中轨
- 反映波动率

## 买卖信号

### 买入信号
1. 价格触及下轨反弹
2. 价格从中轨下方突破中轨
3. 收窄后向上突破上轨

### 卖出信号
1. 价格触及上轨回落
2. 价格从中轨上方跌破中轨
3. 收窄后向下突破下轨

## 特殊形态

### 布林带收窄
- 波动率降低
- 可能有大行情
- 关注突破方向

### 布林带开口
- 波动率增大
- 趋势确认
- 顺势交易

## 策略优化方向

1. **结合成交量**：突破需要成交量确认
2. **多时间框架**：日线+周线确认
3. **带宽过滤**：只在收窄后交易
4. **止损设置**：以中轨或下轨为止损

---

*创建时间：2026-03-21*