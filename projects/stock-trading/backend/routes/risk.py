#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控 API 路由
"""

from http.server import BaseHTTPRequestHandler
import json

def setup_risk_routes(handler: BaseHTTPRequestHandler, path: str, method: str, data: dict, user_id: int, db, send_json):
    """设置风控路由"""
    
    # 获取风控配置
    if path == '/api/risk/config' and method == 'GET':
        from services.risk_control import risk_control
        config = {
            "stop_loss_percent": risk_control.stop_loss_percent,
            "stop_profit_percent": risk_control.stop_profit_percent,
            "max_position_percent": risk_control.max_position_percent,
            "max_total_position": risk_control.max_total_position,
            "daily_loss_limit": risk_control.daily_loss_limit
        }
        send_json({'code': 200, 'data': config})
        return True
    
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
        if 'max_total_position' in config:
            risk_control.max_total_position = config['max_total_position']
        send_json({'code': 200, 'message': '风控配置已更新'})
        return True
    
    # 设置止损
    if path == '/api/risk/stop_loss' and method == 'POST':
        from services.risk_control import risk_control
        stock_code = data.get('stock_code')
        percent = data.get('percent', 0.05)
        risk_control.set_stop_loss(stock_code, percent)
        send_json({'code': 200, 'message': f'已设置 {stock_code} 止损 {percent*100}%'})
        return True
    
    # 风控报告
    if path == '/api/risk/report' and method == 'GET':
        from services.risk_control import risk_control
        positions = db.get_positions(user_id)
        # 获取当前价格
        current_prices = {}
        for pos in positions:
            try:
                quote_data = handler.get_quote(pos['stock_code'])
                if quote_data and 'data' in quote_data:
                    current_prices[pos['stock_code']] = quote_data['data'].get('price', pos['cost_price'])
            except:
                current_prices[pos['stock_code']] = pos['cost_price']
        # 生成报告
        report = risk_control.get_risk_report(positions, current_prices)
        send_json({'code': 200, 'data': report})
        return True
    
    return False

def setup_strategy_routes(handler: BaseHTTPRequestHandler, path: str, method: str, data: dict, user_id: int, db, send_json):
    """设置策略路由"""
    
    # 策略列表
    if path == '/api/strategy/list' and method == 'GET':
        strategies = db.get_strategies(user_id)
        send_json({'code': 200, 'data': {'list': strategies}})
        return True
    
    # 创建策略
    if path == '/api/strategy/create' and method == 'POST':
        name = data.get('name')
        strategy_type = data.get('type', 'ma_cross')
        config = data.get('config', {})
        result = db.create_strategy(user_id, name, strategy_type, json.dumps(config))
        send_json({'code': 200, 'data': result})
        return True
    
    # 启动策略
    if '/api/strategy/' in path and path.endswith('/start'):
        parts = path.split('/')
        strategy_id = int(parts[-2]) if len(parts) > 4 else 0
        # TODO: 实际启动策略
        send_json({'code': 200, 'message': f'策略 {strategy_id} 已启动'})
        return True
    
    # 停止策略
    if '/api/strategy/' in path and path.endswith('/stop'):
        parts = path.split('/')
        strategy_id = int(parts[-2]) if len(parts) > 4 else 0
        # TODO: 实际停止策略
        send_json({'code': 200, 'message': f'策略 {strategy_id} 已停止'})
        return True
    
    # 策略信号
    if path == '/api/strategy/signal' and method == 'POST':
        from services.strategy_executor import SignalGenerator
        stock_code = data.get('stock_code', '000001')
        # 获取历史价格
        try:
            kline = handler.get_kline_data(stock_code, 'day', 30)
            prices = [d['close'] for d in kline.get('data', [])] if kline and 'data' in kline else []
            
            if prices:
                signals = {
                    'ma_cross': SignalGenerator.ma_cross(prices),
                    'rsi': SignalGenerator.rsi_signal(prices),
                    'macd': SignalGenerator.macd_signal(prices)
                }
                send_json({'code': 200, 'data': signals})
            else:
                send_json({'code': 400, 'message': '无法获取价格数据'})
        except Exception as e:
            send_json({'code': 500, 'message': str(e)})
        return True
    
    # 策略状态
    if '/api/strategy/' in path and path.endswith('/status'):
        parts = path.split('/')
        strategy_id = int(parts[-2]) if len(parts) > 4 else 0
        # TODO: 获取实际状态
        send_json({'code': 200, 'data': {'id': strategy_id, 'status': 'running'}})
        return True
    
    return False
