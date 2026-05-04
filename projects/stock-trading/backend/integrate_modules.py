#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控和策略 API 路由
添加到 simple_server.py 末尾
"""

# ============ 风控 API ============

# 获取风控配置
if path == '/api/risk/config':
    from services.risk_control import risk_control
    config = {
        "stop_loss_percent": risk_control.stop_loss_percent,
        "stop_profit_percent": risk_control.stop_profit_percent,
        "max_position_percent": risk_control.max_position_percent,
        "max_total_position": risk_control.max_total_position
    }
    self.send_json({'code': 200, 'data': config})
    return

# 更新风控配置
if path == '/api/risk/config' and method == 'POST':
    from services.risk_control import risk_control
    config = data.get('config', {})
    if 'stop_loss_percent' in config:
        risk_control.stop_loss_percent = config['stop_loss_percent']
    if 'stop_profit_percent' in config:
        risk_control.stop_profit_percent = config['stop_profit_percent']
    if 'max_position_percent' in config:
        risk_control.max_position_percent = config['max_position_percent']
    self.send_json({'code': 200, 'message': '风控配置已更新'})
    return

# 设置止损
if path == '/api/risk/stop_loss' and method == 'POST':
    from services.risk_control import risk_control
    stock_code = data.get('stock_code')
    percent = data.get('percent', 0.05)
    risk_control.set_stop_loss(stock_code, percent)
    self.send_json({'code': 200, 'message': f'已设置 {stock_code} 止损 {percent*100}%'})
    return

# 风控报告
if path == '/api/risk/report':
    from services.risk_control import risk_control
    # 获取持仓
    positions = db.get_positions(user_id)
    # 获取当前价格
    current_prices = {}
    for pos in positions:
        quote = get_quote(pos['stock_code'])
        if quote:
            current_prices[pos['stock_code']] = quote['price']
    # 生成报告
    report = risk_control.get_risk_report(positions, current_prices)
    self.send_json({'code': 200, 'data': report})
    return

# ============ 策略 API ============

# 策略列表
if path == '/api/strategy/list':
    strategies = db.get_strategies(user_id)
    self.send_json({'code': 200, 'data': {'list': strategies}})
    return

# 创建策略
if path == '/api/strategy/create' and method == 'POST':
    name = data.get('name')
    strategy_type = data.get('type', 'ma_cross')
    config = data.get('config', {})
    result = db.create_strategy(user_id, name, strategy_type, json.dumps(config))
    self.send_json({'code': 200, 'data': result})
    return

# 启动策略
if path.startswith('/api/strategy/') and path.endswith('/start'):
    strategy_id = int(path.split('/')[-2])
    # TODO: 实际启动策略
    self.send_json({'code': 200, 'message': f'策略 {strategy_id} 已启动'})
    return

# 停止策略
if path.startswith('/api/strategy/') and path.endswith('/stop'):
    strategy_id = int(path.split('/')[-2])
    # TODO: 实际停止策略
    self.send_json({'code': 200, 'message': f'策略 {strategy_id} 已停止'})
    return

# 策略信号
if path == '/api/strategy/signal':
    from services.strategy_executor import SignalGenerator
    stock_code = data.get('stock_code', '000001')
    # 获取历史价格
    kline = get_kline_data(stock_code, 'day', 30)
    prices = [d['close'] for d in kline.get('data', [])]
    
    signals = {
        'ma_cross': SignalGenerator.ma_cross(prices),
        'rsi': SignalGenerator.rsi_signal(prices),
        'macd': SignalGenerator.macd_signal(prices)
    }
    
    self.send_json({'code': 200, 'data': signals})
    return