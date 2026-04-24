#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国知网专利数据爬虫
目标网站: https://kns.cnki.net/kns8s/
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, quote

def get_cnki_patents():
    """爬取中国知网专利数据"""
    
    base_url = "https://kns.cnki.net/kns8s/"
    
    # 模拟浏览器头信息
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    patents = []
    
    try:
        print("🔍 正在访问中国知网专利页面...")
        
        # 访问知网首页获取必要的cookie等信息
        session = requests.Session()
        response = session.get(base_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ 访问失败，状态码: {response.status_code}")
            return patents
        
        # 构建专利搜索URL（示例搜索关键词）
        search_keywords = ["人工智能", "机器学习", "深度学习", "自然语言处理"]
        
        for keyword in search_keywords:
            print(f"🔎 正在搜索专利关键词: {keyword}")
            
            # 构建搜索URL（这里需要根据实际网站结构调整）
            search_url = f"{base_url}DefaultResult/index?kw={quote(keyword)}&db=SCPD"
            
            try:
                search_response = session.get(search_url, headers=headers, timeout=30)
                
                if search_response.status_code == 200:
                    soup = BeautifulSoup(search_response.text, 'html.parser')
                    
                    # 解析专利结果（需要根据实际HTML结构调整）
                    patent_items = soup.find_all('div', class_=re.compile(r'patent|result'))
                    
                    for item in patent_items[:5]:  # 限制每个关键词最多5条
                        patent_data = parse_patent_item(item, keyword)
                        if patent_data:
                            patents.append(patent_data)
                            print(f"✅ 提取专利: {patent_data.get('title', '未知')}")
                
                # 礼貌延迟
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ 搜索关键词 {keyword} 时出错: {e}")
                continue
    
    except Exception as e:
        print(f"❌ 爬虫执行出错: {e}")
    
    return patents

def parse_patent_item(item, keyword):
    """解析单个专利条目"""
    
    try:
        # 这里需要根据实际的HTML结构来解析
        # 示例解析逻辑，需要根据实际网站调整
        
        title_elem = item.find('a', class_=re.compile(r'title|name'))
        patent_no_elem = item.find('span', class_=re.compile(r'number|no'))
        applicant_elem = item.find('span', class_=re.compile(r'applicant|owner'))
        inventor_elem = item.find('span', class_=re.compile(r'inventor|author'))
        date_elem = item.find('span', class_=re.compile(r'date|time'))
        
        patent_data = {
            'keyword': keyword,
            'title': title_elem.get_text(strip=True) if title_elem else '未知标题',
            'patent_number': patent_no_elem.get_text(strip=True) if patent_no_elem else '未知专利号',
            'applicant': applicant_elem.get_text(strip=True) if applicant_elem else '未知申请人',
            'inventor': inventor_elem.get_text(strip=True) if inventor_elem else '未知发明人',
            'application_date': date_elem.get_text(strip=True) if date_elem else '未知日期',
            'abstract': extract_abstract(item),
            'source': '中国知网',
            'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return patent_data
        
    except Exception as e:
        print(f"⚠️ 解析专利条目出错: {e}")
        return None

def extract_abstract(item):
    """提取专利摘要"""
    try:
        abstract_elem = item.find('div', class_=re.compile(r'abstract|summary'))
        if abstract_elem:
            return abstract_elem.get_text(strip=True)[:200] + '...'  # 限制长度
        return '暂无摘要'
    except:
        return '暂无摘要'

def save_patents_data(patents):
    """保存专利数据"""
    
    if not patents:
        print("⚠️ 没有提取到专利数据")
        return
    
    # 保存为JSON文件
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"/root/.openclaw/workspace/data/cnki_patents_{timestamp}.json"
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(patents, f, ensure_ascii=False, indent=2)
    
    print(f"💾 专利数据已保存到: {filename}")
    
    # 生成简报告
    generate_report(patents, filename)
    
    return filename

def generate_report(patents, data_file):
    """生成爬取报告"""
    
    report = {
        'total_patents': len(patents),
        'keywords': list(set([p['keyword'] for p in patents])),
        'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'data_file': data_file,
        'summary': f"成功爬取 {len(patents)} 条专利数据"
    }
    
    report_file = data_file.replace('.json', '_report.json')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📊 爬取报告已生成: {report_file}")

def main():
    """主函数"""
    print("🚀 开始爬取中国知网专利数据...")
    print("📋 目标网站: https://kns.cnki.net/kns8s/")
    print("⏰ 开始时间:", time.strftime('%Y-%m-%d %H:%M:%S'))
    print("-" * 50)
    
    # 执行爬取
    patents = get_cnki_patents()
    
    print("-" * 50)
    print(f"✅ 爬取完成! 共获取 {len(patents)} 条专利数据")
    
    # 保存数据
    if patents:
        data_file = save_patents_data(patents)
        print(f"🎯 数据文件: {data_file}")
    
    print("⏰ 结束时间:", time.strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    import os
    main()