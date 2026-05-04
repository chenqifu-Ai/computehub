#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Patents 演示爬虫
作为CNKI的替代方案
"""

import requests
import time
import json
import csv
from bs4 import BeautifulSoup
from urllib.parse import quote

class GooglePatentsCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        })
        self.base_url = "https://patents.google.com"
        self.results = []
    
    def search_patents(self, keywords, max_results=10):
        """搜索专利"""
        try:
            encoded_keywords = quote(keywords)
            url = f"{self.base_url}/?q={encoded_keywords}&num={max_results}"
            
            print(f"正在搜索: {keywords}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return self.parse_results(response.text)
            else:
                print(f"请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"搜索过程中发生错误: {e}")
            return False
    
    def parse_results(self, html_content):
        """解析搜索结果"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找专利结果
            patent_items = soup.find_all('article', {'itemtype': 'http://schema.org/Patent'})
            
            if not patent_items:
                print("未找到专利结果")
                return False
            
            print(f"找到 {len(patent_items)} 条专利")
            
            for item in patent_items:
                patent_data = self.extract_patent_info(item)
                if patent_data:
                    self.results.append(patent_data)
            
            return True
            
        except Exception as e:
            print(f"解析结果时发生错误: {e}")
            return False
    
    def extract_patent_info(self, item):
        """提取专利信息"""
        try:
            # 标题
            title_elem = item.find('h3')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 链接
            link_elem = item.find('a', {'itemprop': 'url'})
            link = link_elem['href'] if link_elem and link_elem.get('href') else ""
            if link and not link.startswith('http'):
                link = self.base_url + link
            
            # 专利号
            patent_no_elem = item.find('span', {'itemprop': 'publicationNumber'})
            patent_no = patent_no_elem.get_text(strip=True) if patent_no_elem else ""
            
            # 发明人
            inventors = []
            inventor_elems = item.find_all('span', {'itemprop': 'inventor'})
            for elem in inventor_elems:
                inventors.append(elem.get_text(strip=True))
            
            # 申请日期
            date_elem = item.find('span', {'itemprop': 'filingDate'})
            filing_date = date_elem.get_text(strip=True) if date_elem else ""
            
            patent_info = {
                'title': title,
                'link': link,
                'patent_number': patent_no,
                'inventors': ", ".join(inventors),
                'filing_date': filing_date,
                'source': 'Google Patents',
                'crawled_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"✓ {patent_no}: {title}")
            return patent_info
            
        except Exception as e:
            print(f"提取专利信息时发生错误: {e}")
            return None
    
    def save_results(self, format='json'):
        """保存结果"""
        if not self.results:
            print("没有结果可保存")
            return None
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f"google_patents_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        elif format == 'csv':
            filename = f"google_patents_{timestamp}.csv"
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['title', 'link', 'patent_number', 'inventors', 'filing_date', 'source', 'crawled_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        
        return filename

def main():
    """主函数"""
    print("=== Google Patents 演示爬虫 ===")
    print("作为CNKI的替代方案")
    
    crawler = GooglePatentsCrawler()
    
    # 搜索示例
    search_keywords = "machine learning"  # 使用英文关键词
    max_results = 8
    
    print(f"搜索关键词: {search_keywords}")
    
    # 执行搜索
    success = crawler.search_patents(search_keywords, max_results)
    
    if success and crawler.results:
        print(f"\n✅ 成功爬取 {len(crawler.results)} 条专利")
        
        # 显示结果
        print("\n=== 专利列表 ===")
        for i, patent in enumerate(crawler.results, 1):
            print(f"{i}. {patent['title']}")
            print(f"   专利号: {patent['patent_number']}")
            print(f"   发明人: {patent['inventors']}")
            print(f"   链接: {patent['link']}")
            print()
        
        # 保存结果
        json_file = crawler.save_results('json')
        csv_file = crawler.save_results('csv')
        
        print(f"📊 JSON数据: {json_file}")
        print(f"📋 CSV表格: {csv_file}")
        
    else:
        print("\n❌ 爬取失败")
        print("可能的原因:")
        print("1. 网络连接问题")
        print("2. 网站结构变化")
        print("3. 反爬机制")

if __name__ == "__main__":
    main()