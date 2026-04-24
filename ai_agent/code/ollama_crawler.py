#!/usr/bin/env python3
"""
Ollama.com 数据爬取与分析脚本
网络专家任务：爬取ollama.com数据并进行分析
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

def fetch_ollama_data():
    """爬取Ollama.com网站数据"""
    print("🔍 开始爬取 Ollama.com 数据...")
    
    try:
        # 设置请求头模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 请求Ollama官网
        response = requests.get('https://ollama.com', headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取关键信息
        data = {
            'title': extract_title(soup),
            'description': extract_description(soup),
            'models': extract_models(soup),
            'features': extract_features(soup),
            'download_info': extract_download_info(soup),
            'community': extract_community_info(soup),
            'timestamp': datetime.now().isoformat(),
            'url': 'https://ollama.com',
            'status_code': response.status_code
        }
        
        print("✅ 数据爬取成功")
        return data
        
    except requests.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}

def extract_title(soup):
    """提取页面标题"""
    title_tag = soup.find('title')
    return title_tag.get_text().strip() if title_tag else 'No title found'

def extract_description(soup):
    """提取页面描述"""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    return meta_desc['content'].strip() if meta_desc and 'content' in meta_desc.attrs else 'No description'

def extract_models(soup):
    """提取模型信息"""
    models = []
    # 查找模型相关元素
    model_elements = soup.find_all(['h2', 'h3', 'div'], class_=lambda x: x and 'model' in x.lower())
    
    for element in model_elements[:5]:  # 取前5个
        models.append(element.get_text().strip())
    
    return models if models else ['No model information found']

def extract_features(soup):
    """提取特性信息"""
    features = []
    # 查找特性相关元素
    feature_elements = soup.find_all(['li', 'div'], class_=lambda x: x and ('feature' in x.lower() or 'benefit' in x.lower()))
    
    for element in feature_elements[:10]:  # 取前10个
        features.append(element.get_text().strip())
    
    return features if features else ['No feature information found']

def extract_download_info(soup):
    """提取下载信息"""
    download_info = {}
    # 查找下载按钮或链接
    download_buttons = soup.find_all('a', href=lambda x: x and 'download' in x.lower())
    
    for button in download_buttons[:3]:
        text = button.get_text().strip()
        href = button.get('href', '')
        if text and href:
            download_info[text] = href
    
    return download_info if download_info else {'No download info': ''}

def extract_community_info(soup):
    """提取社区信息"""
    community = {}
    # 查找社区链接
    social_links = soup.find_all('a', href=lambda x: x and any(platform in x for platform in 
                                                           ['github.com', 'discord.gg', 'twitter.com', 'x.com']))
    
    for link in social_links:
        text = link.get_text().strip() or 'Social Link'
        href = link.get('href', '')
        community[text] = href
    
    return community if community else {'No community links': ''}

def analyze_data(data):
    """分析爬取的数据"""
    print("\n🧠 开始数据分析...")
    
    analysis = {
        'summary': '',
        'key_insights': [],
        'recommendations': [],
        'technical_analysis': {}
    }
    
    # 基础分析
    if 'error' in data:
        analysis['summary'] = '数据爬取失败，无法进行分析'
        analysis['key_insights'].append(f'错误信息: {data["error"]}')
        return analysis
    
    # 网站状态分析
    analysis['technical_analysis']['website_status'] = f"状态码: {data.get('status_code', 'Unknown')}"
    analysis['technical_analysis']['response_time'] = datetime.now().isoformat()
    
    # 内容分析
    title = data.get('title', '')
    analysis['summary'] = f"成功爬取: {title}"
    
    # 关键洞察
    if 'ollama' in title.lower():
        analysis['key_insights'].append("✅ 网站主题确认: Ollama AI平台")
    
    if data.get('models'):
        analysis['key_insights'].append(f"📊 发现 {len(data['models'])} 个模型相关信息")
    
    if data.get('features'):
        analysis['key_insights'].append(f"⭐ 发现 {len(data['features'])} 个特性功能")
    
    if data.get('download_info'):
        analysis['key_insights'].append(f"📥 发现 {len(data['download_info'])} 个下载选项")
    
    # 网络专家建议
    analysis['recommendations'].append("🔧 建议: 定期监控Ollama版本更新")
    analysis['recommendations'].append("📈 建议: 分析模型发布频率和趋势")
    analysis['recommendations'].append("🤝 建议: 关注社区活跃度和开发者动态")
    
    print("✅ 数据分析完成")
    return analysis

def save_results(data, analysis):
    """保存结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/root/.openclaw/workspace/ai_agent/results/ollama_analysis_{timestamp}.json"
    
    result = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'tool': 'Ollama Crawler',
            'version': '1.0'
        },
        'raw_data': data,
        'analysis': analysis
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存: {filename}")
    return filename

def main():
    """主函数"""
    print("=" * 60)
    print("🤖 网络专家任务: Ollama.com 数据爬取与分析")
    print("=" * 60)
    
    # 爬取数据
    data = fetch_ollama_data()
    
    # 分析数据
    analysis = analyze_data(data)
    
    # 保存结果
    if 'error' not in data:
        filename = save_results(data, analysis)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("📋 执行摘要:")
    print("=" * 60)
    print(analysis['summary'])
    
    print("\n🔍 关键洞察:")
    for insight in analysis['key_insights']:
        print(f"  • {insight}")
    
    print("\n💡 专家建议:")
    for recommendation in analysis['recommendations']:
        print(f"  • {recommendation}")
    
    print("\n" + "=" * 60)
    print("✅ 网络专家任务完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()