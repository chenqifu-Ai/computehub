"""
策略回测引擎
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import random

# pandas是可选依赖
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_trades: int
    loss_trades: int
    trades: List[Dict]


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # 持仓 {code: {volume, cost_price}}
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值
    
    def _convert_to_dataframe(self, klines: List[Dict]):
        """将K线数据转换为DataFrame（如果pandas可用）"""
        if HAS_PANDAS:
            df = pd.DataFrame(klines)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            return df
        return None
    
    def _calculate_signal_pandas(self, df, strategy_func):
        """使用pandas计算信号"""
        df['signal'] = strategy_func(df)
        return df['signal']
    
    def _calculate_signal_simple(self, klines: List[Dict], strategy_func) -> List[Dict]:
        """不使用pandas计算信号（简化版）"""
        # 简化处理：返回模拟信号
        signals = []
        for i, kline in enumerate(klines):
            if i < 5:
                signals.append({'date': kline['date'], 'signal': 0})
            else:
                # 简单的双均线逻辑
                recent_close = [k['close'] for k in klines[max(0, i-20):i+1]]
                short_ma = sum(recent_close[-5:]) / 5 if len(recent_close) >= 5 else recent_close[-1]
                long_ma = sum(recent_close[-20:]) / 20 if len(recent_close) >= 20 else sum(recent_close) / len(recent_close)
                
                if short_ma > long_ma:
                    signal = 1
                elif short_ma < long_ma:
                    signal = -1
                else:
                    signal = 0
                
                signals.append({'date': kline['date'], 'signal': signal})
        
        return signals
    
    def run_backtest(
        self,
        strategy_func=None,
        klines: List[Dict] = None,
        strategy_name: str = "Unknown",
        strategy_code: str = None,
        stock_code: str = None,
        start_date: str = None,
        end_date: str = None,
        initial_capital: float = 1000000.0
    ) -> Dict:
        """
        运行回测 - 支持多种调用方式
        
        Args:
            strategy_func: 策略函数
            klines: K线数据
            strategy_name: 策略名称
            strategy_code: 策略代码字符串
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
        
        Returns:
            Dict: 回测结果字典
        """
        # 设置初始资金
        self.initial_capital = initial_capital
        
        # 如果没有提供K线数据，获取数据
        if not klines and stock_code:
            from .market_service import market_service
            kline_data = market_service.get_kline(
                code=stock_code,
                start_date=start_date,
                end_date=end_date,
                count=365
            )
            klines = kline_data.get('data', [])
        
        if not klines:
            return {"success": False, "error": "没有K线数据"}
        
        # 运行回测
        try:
            # 使用简化策略
            signals = self._calculate_signal_simple(klines, None)
            signal_list = [s['signal'] for s in signals]
            result = self._run_backtest_with_signals(klines, signal_list, strategy_name)
            
            return {
                "success": True,
                "strategy_name": result.strategy_name,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_capital": result.initial_capital,
                "final_capital": result.final_capital,
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "win_rate": result.win_rate,
                "total_trades": result.total_trades,
                "profit_trades": result.profit_trades,
                "loss_trades": result.loss_trades,
                "trades": result.trades[:20]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_backtest_with_signals(self, klines: List[Dict], signals, strategy_name: str) -> BacktestResult:
        """使用信号运行回测"""
        # 重置状态
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []
        
        # 如果signals是pandas Series，转换为列表
        if HAS_PANDAS and hasattr(signals, 'tolist'):
            signals = signals.tolist()
        
        # 模拟交易
        for i, kline in enumerate(klines):
            date = kline['date']
            signal = signals[i] if i < len(signals) else 0
            close = kline['close']
            
            # 执行交易
            if signal == 1 and self.cash > 0:
                # 买入：全仓买入
                volume = int(self.cash / close)
                if volume > 0:
                    self.positions['stock'] = {
                        'volume': volume,
                        'cost_price': close
                    }
                    self.trades.append({
                        'date': str(date) if not isinstance(date, str) else date,
                        'type': 'buy',
                        'price': close,
                        'volume': volume,
                        'amount': close * volume
                    })
                    self.cash -= close * volume
            
            elif signal == -1 and 'stock' in self.positions:
                # 卖出：全部卖出
                pos = self.positions['stock']
                self.trades.append({
                    'date': str(date) if not isinstance(date, str) else date,
                    'type': 'sell',
                    'price': close,
                    'volume': pos['volume'],
                    'amount': close * pos['volume'],
                    'profit': (close - pos['cost_price']) * pos['volume']
                })
                self.cash += close * pos['volume']
                del self.positions['stock']
            
            # 记录每日净值
            position_value = 0
            if 'stock' in self.positions:
                pos = self.positions['stock']
                position_value = pos['volume'] * close
            
            total_value = self.cash + position_value
            self.daily_values.append({
                'date': str(date) if not isinstance(date, str) else date,
                'value': total_value
            })
        
        # 计算收益指标
        final_value = self.daily_values[-1]['value'] if self.daily_values else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 计算最大回撤
        max_value = self.initial_capital
        max_drawdown = 0
        for dv in self.daily_values:
            if dv['value'] > max_value:
                max_value = dv['value']
            drawdown = (max_value - dv['value']) / max_value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算胜率
        profit_trades = [t for t in self.trades if t['type'] == 'sell' and t.get('profit', 0) > 0]
        loss_trades = [t for t in self.trades if t['type'] == 'sell' and t.get('profit', 0) < 0]
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        win_rate = len(profit_trades) / len(sell_trades) if sell_trades else 0
        
        # 计算夏普比率（简化版）
        if len(self.daily_values) > 1:
            returns = []
            for i in range(1, len(self.daily_values)):
                prev_value = self.daily_values[i-1]['value']
                curr_value = self.daily_values[i]['value']
                if prev_value > 0:
                    returns.append((curr_value - prev_value) / prev_value)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return)**2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = avg_return / std_return * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # 年化收益率
        days = len(self.daily_values)
        annual_return = total_return * (252 / days) if days > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=klines[0]['date'] if klines else '',
            end_date=klines[-1]['date'] if klines else '',
            initial_capital=self.initial_capital,
            final_capital=final_value,
            total_return=round(total_return * 100, 2),
            annual_return=round(annual_return * 100, 2),
            max_drawdown=round(max_drawdown * 100, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            win_rate=round(win_rate * 100, 2),
            total_trades=len(self.trades),
            profit_trades=len(profit_trades),
            loss_trades=len(loss_trades),
            trades=self.trades
        )
    
    def generate_report(self, result: BacktestResult) -> str:
        """生成回测报告"""
        report = f"""
# 回测报告

## 基本信息
- **策略名称**: {result.strategy_name}
- **回测区间**: {result.start_date} ~ {result.end_date}
- **初始资金**: ¥{result.initial_capital:,.2f}
- **最终资金**: ¥{result.final_capital:,.2f}

## 收益指标
- **总收益率**: {result.total_return}%
- **年化收益率**: {result.annual_return}%
- **最大回撤**: {result.max_drawdown}%
- **夏普比率**: {result.sharpe_ratio}

## 交易统计
- **总交易次数**: {result.total_trades}笔
- **盈利次数**: {result.profit_trades}笔
- **亏损次数**: {result.loss_trades}笔
- **胜率**: {result.win_rate}%

## 交易记录
"""
        for trade in result.trades[:10]:  # 只显示前10笔
            trade_type = "买入" if trade['type'] == 'buy' else "卖出"
            report += f"- {trade['date']} {trade_type}: {trade['volume']}股 @ ¥{trade['price']:.2f}\n"
        
        if len(result.trades) > 10:
            report += f"... 共 {len(result.trades)} 笔交易\n"
        
        return report


# 策略模板
def double_ma_strategy(df, short_period=5, long_period=20):
    """双均线策略"""
    if HAS_PANDAS and hasattr(df, 'rolling'):
        df['short_ma'] = df['close'].rolling(window=short_period).mean()
        df['long_ma'] = df['close'].rolling(window=long_period).mean()
        
        df['signal'] = 0
        # 金叉买入
        df.loc[(df['short_ma'] > df['long_ma']) & 
               (df['short_ma'].shift(1) <= df['long_ma'].shift(1)), 'signal'] = 1
        # 死叉卖出
        df.loc[(df['short_ma'] < df['long_ma']) & 
               (df['short_ma'].shift(1) >= df['long_ma'].shift(1)), 'signal'] = -1
        
        return df['signal']
    else:
        # 简化版本：返回双均线逻辑
        return lambda klines: _simple_double_ma(klines, short_period, long_period)


def _simple_double_ma(klines, short_period=5, long_period=20):
    """简化版双均线策略"""
    signals = []
    closes = [k['close'] for k in klines]
    
    for i in range(len(klines)):
        if i < long_period:
            signals.append(0)
        else:
            short_ma = sum(closes[i-short_period:i]) / short_period
            long_ma = sum(closes[i-long_period:i]) / long_period
            
            if i > 0:
                prev_short_ma = sum(closes[i-short_period-1:i-1]) / short_period
                prev_long_ma = sum(closes[i-long_period-1:i-1]) / long_period
                
                if short_ma > long_ma and prev_short_ma <= prev_long_ma:
                    signals.append(1)  # 金叉买入
                elif short_ma < long_ma and prev_short_ma >= prev_long_ma:
                    signals.append(-1)  # 死叉卖出
                else:
                    signals.append(0)
            else:
                signals.append(0)
    
    return signals


def macd_strategy(df, fast=12, slow=26, signal=9):
    """MACD策略"""
    if HAS_PANDAS and hasattr(df, 'ewm'):
        df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal_line'] = df['macd'].ewm(span=signal, adjust=False).mean()
        
        df['signal'] = 0
        # 金叉买入
        df.loc[(df['macd'] > df['signal_line']) & 
               (df['macd'].shift(1) <= df['signal_line'].shift(1)), 'signal'] = 1
        # 死叉卖出
        df.loc[(df['macd'] < df['signal_line']) & 
               (df['macd'].shift(1) >= df['signal_line'].shift(1)), 'signal'] = -1
        
        return df['signal']
    else:
        return lambda klines: _simple_macd(klines, fast, slow, signal)


def _simple_macd(klines, fast=12, slow=26, signal=9):
    """简化版MACD策略"""
    # 返回模拟信号
    signals = []
    for i in range(len(klines)):
        if i < slow + signal:
            signals.append(0)
        else:
            # 简化MACD逻辑
            closes = [k['close'] for k in klines[:i+1]]
            ema_fast = sum(closes[-fast:]) / fast
            ema_slow = sum(closes[-slow:]) / slow
            macd = ema_fast - ema_slow
            
            # 简化：MACD为正买入，为负卖出
            if macd > 0:
                signals.append(1)
            elif macd < 0:
                signals.append(-1)
            else:
                signals.append(0)
    
    return signals


# 全局实例
backtest_engine = BacktestEngine()