#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
达达单号查询脚本 - 3045504220093780706
"""

import requests
from bs4 import BeautifulSoup
import json

def check_dada_direct():
    """尝试直接到达达官网查询"""
    print("🔍 尝试到达达官网查询...")
    
    dada_number = "3045504220093780706"
    
    # 达达查询API端点 (常见模式)
    endpoints = [
        f"https://www.imdada.cn/tracking/{dada_number}",
        f"https://api.imdada.cn/track/v2/query?orderNo={dada_number}",
        f"https://www.imdada.cn/order/track?orderNo={dada_number}",
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                print(f"✅ 可达: {url}")
                
                # 尝试解析JSON或HTML
                if 'application/json' in response.headers.get('content-type', ''):
                    try:
                        data = response.json()
                        print(f"📦 JSON响应: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
                        return True
                    except:
                        print("📄 响应内容:", response.text[:200])
                else:
                    # HTML页面
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title = soup.find('title')
                    if title:
                        print(f"📄 页面标题: {title.text}")
                    
                    # 查找物流信息
                    tracking_info = soup.find_all(['div', 'span'], class_=lambda x: x and ('track' in x.lower() or 'logistics' in x.lower() or 'express' in x.lower()))
                    if tracking_info:
                        print("🚚 找到物流信息元素")
                    
                    return True
                    
            else:
                print(f"❌ {url} - 状态码: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"❌ 请求失败: {url} - {e}")
        except Exception as e:
            print(f"❌ 解析错误: {e}")
    
    return False

def check_third_party_platforms():
    """检查第三方快递查询平台"""
    print("\n🔍 检查第三方平台...")
    
    platforms = [
        ("快递100", f"https://www.kuaidi100.com/query?type=dada&postid={3045504220093780706}"),
        ("菜鸟裹裹", f"https://www.cainiao.com/detail.htm?mailNo={3045504220093780706}"),
        ("17track", f"https://www.17track.net/zh-cn/track?nums={3045504220093780706}"),
    ]
    
    for name, url in platforms:
        try:
            response = requests.get(url, timeout=8, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                print(f"✅ {name}: 可访问")
                
                # 检查是否包含物流信息
                if 'track' in response.text.lower() or '物流' in response.text or 'express' in response.text.lower():
                    print(f"   📦 可能包含物流信息")
                
            else:
                print(f"❌ {name}: 状态码 {response.status_code}")
                
        except requests.RequestException:
            print(f"❌ {name}: 访问失败")

def generate_query_links():
    """生成查询链接"""
    number = "3045504220093780706"
    
    links = [
        ("达达官网", f"https://www.imdada.cn/tracking/{number}"),
        ("快递100", f"https://www.kuaidi100.com/?nu={number}"),
        ("菜鸟裹裹", f"https://www.cainiao.com/detail.htm?mailNo={number}"),
        ("17TRACK", f"https://www.17track.net/zh-cn/track?nums={number}"),
        ("快递鸟", f"https://www.kdniao.com/tracking/{number}"),
    ]
    
    print("\n🔗 直接查询链接:")
    for name, url in links:
        print(f"   {name}: {url}")

def main():
    """主函数"""
    print("🚚 达达单号查询: 3045504220093780706")
    print("=" * 60)
    
    # 尝试直接查询
    if not check_dada_direct():
        print("\n❌ 直接查询失败，尝试第三方平台...")
        check_third_party_platforms()
    
    # 生成查询链接
    generate_query_links()
    
    print("\n" + "=" * 60)
    print("🎯 手动查询建议:")
    print("1. 访问达达官网: https://www.imdada.cn/")
    print("2. 输入单号: 3045504220093780706") 
    print("3. 或使用快递100等第三方平台")
    print("\n💡 该单号可能是:")
    print("   - 达达物流运单")
    print("   - 同城配送订单")
    print("   - 快递跟踪编号")

if __name__ == "__main__":
    main()