#!/usr/bin/env python3
"""
快递单号查询工具
查询单号 KY4000997929844 的物流信息
"""

import requests
import json
from datetime import datetime

def identify_express_company(express_number):
    """识别快递公司"""
    # 常见快递公司单号前缀
    company_prefixes = {
        'KY': '跨越速运',
        'SF': '顺丰速运',
        'YT': '圆通速递',
        'ZD': '韵达快递',
        'ST': '申通快递',
        'ZT': '中通快递',
        'YD': '韵达快递',
        'EMS': 'EMS',
        'JD': '京东物流',
        'DBL': '德邦物流',
        'ZTO': '中通快递',
    }
    
    # 检查前缀
    for prefix, company in company_prefixes.items():
        if express_number.startswith(prefix):
            return company
    
    # 根据长度和格式判断
    if len(express_number) == 13 and express_number.isdigit():
        return '韵达/中通/圆通'
    elif len(express_number) == 12 and express_number.isdigit():
        return '申通快递'
    elif len(express_number) == 10 and express_number.isdigit():
        return 'EMS'
    
    return '未知快递公司'

def query_kuaidi100(express_number, company_code=None):
    """查询快递100"""
    # 如果没有指定公司，尝试自动识别
    if not company_code:
        company_code = 'ky'  # 默认尝试跨越速运
    
    url = f'https://www.kuaidi100.com/query'
    params = {
        'type': company_code,
        'postid': express_number,
        'id': 1,
        'valicode': '',
        'temp': '0.123456789'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.kuaidi100.com/'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'HTTP错误: {response.status_code}'}
    except Exception as e:
        return {'error': f'查询失败: {str(e)}'}

def query_other_platforms(express_number):
    """尝试其他查询平台"""
    platforms = [
        {
            'name': '快递100',
            'url': f'https://www.kuaidi100.com/?nu={express_number}'
        },
        {
            'name': '菜鸟裹裹',
            'url': f'https://www.cainiao.com/index.html?mailNo={express_number}'
        },
        {
            'name': '快递鸟',
            'url': f'https://www.kdniao.com/tracking?number={express_number}'
        }
    ]
    
    return platforms

def main():
    express_number = 'KY4000997929844'
    
    print(f"🚚 查询快递单号: {express_number}")
    print("=" * 50)
    
    # 识别快递公司
    company = identify_express_company(express_number)
    print(f"📦 识别结果: {company}")
    
    # 查询快递100
    print(f"\n🔍 正在查询快递100...")
    result = query_kuaidi100(express_number)
    
    if 'error' in result:
        print(f"❌ 查询失败: {result['error']}")
    else:
        print(f"✅ 查询成功!")
        print(f"状态: {result.get('state', '未知')}")
        print(f"消息: {result.get('message', '无')}")
        
        if 'data' in result and result['data']:
            print(f"\n📋 物流轨迹:")
            for i, item in enumerate(result['data'], 1):
                print(f"{i}. {item.get('time', '')} - {item.get('context', '')}")
    
    # 提供其他查询方式
    print(f"\n🌐 其他查询方式:")
    platforms = query_other_platforms(express_number)
    for platform in platforms:
        print(f"   • {platform['name']}: {platform['url']}")
    
    print(f"\n💡 建议: 如果自动查询失败，可以手动复制单号到上述网站查询")

if __name__ == "__main__":
    main()