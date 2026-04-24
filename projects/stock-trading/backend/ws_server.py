#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 实时推送服务
"""

import asyncio
import json
from datetime import datetime
from typing import Set
import threading

class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.connections: Set = set()
        self.running = False
        self._loop = None
    
    async def connect(self, websocket):
        """新连接"""
        self.connections.add(websocket)
        print(f"WebSocket 连接建立，当前连接数：{len(self.connections)}")
    
    async def disconnect(self, websocket):
        """断开连接"""
        self.connections.discard(websocket)
        print(f"WebSocket 连接断开，当前连接数：{len(self.connections)}")
    
    async def broadcast(self, message: dict):
        """广播消息"""
        if not self.connections:
            return
        
        message["timestamp"] = datetime.now().isoformat()
        message_json = json.dumps(message, ensure_ascii=False)
        
        # 发送给所有连接
        disconnected = set()
        for ws in self.connections:
            try:
                await ws.send_text(message_json)
            except:
                disconnected.add(ws)
        
        # 清理断开的连接
        self.connections -= disconnected
    
    async def push_quote(self, stock_code: str, quote_data: dict):
        """推送行情"""
        await self.broadcast({
            "type": "quote",
            "stock_code": stock_code,
            "data": quote_data
        })
    
    async def push_order(self, order_data: dict):
        """推送订单"""
        await self.broadcast({
            "type": "order",
            "data": order_data
        })
    
    async def push_position(self, position_data: dict):
        """推送持仓"""
        await self.broadcast({
            "type": "position",
            "data": position_data
        })
    
    async def push_signal(self, signal_data: dict):
        """推送信号"""
        await self.broadcast({
            "type": "signal",
            "data": signal_data
        })

# 全局 WebSocket 管理器
ws_manager = WebSocketManager()

# 行情推送任务
async def quote_pusher():
    """定时推送行情"""
    import random
    
    stock_codes = ["000001", "600519", "002594", "300750", "601318"]
    
    while ws_manager.running:
        for code in stock_codes:
            # 模拟行情变化
            quote = {
                "code": code,
                "price": random.uniform(10, 100),
                "change": random.uniform(-5, 5),
                "volume": random.randint(10000, 100000)
            }
            await ws_manager.push_quote(code, quote)
        
        await asyncio.sleep(3)  # 每 3 秒推送一次

def start_ws_server():
    """启动 WebSocket 服务"""
    ws_manager.running = True
    asyncio.create_task(quote_pusher())
    print("✅ WebSocket 服务已启动")