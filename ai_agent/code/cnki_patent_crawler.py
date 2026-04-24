#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国知网(CNKI)专利爬虫工具
用于爬取专利信息并保存为结构化数据
"""

import requests
import time
import json
import csv
import re
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode

class CNKIPatentCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.base_url = "https://kns.cnki.net"
        self.search_url = "https://kns.cnki.net/kns8/AdvSearch"
        self.results = []
    
    def search_patents(self, keywords, max_results=50):
        """搜索专利"""
        try:
            # 先获取搜索页面获取必要的参数
            print("正在访问CNKI搜索页面...")
            response = self.session.get(self.search_url)
            
            if response.status_code != 200:
                print(f"无法访问搜索页面: {response.status_code}")
                return False
            
            # 构造搜索参数（这里需要根据实际页面结构调整）
            search_params = {
                'dbcode': 'SCPD',  # 专利数据库
                'kw': keywords,
                'page': 1,
                'size': 20
            }
            
            # 尝试搜索
            search_response = self.session.post(
                f"{self.base_url}/kns8/defaultresult/index",
                data=search_params,
                timeout=30
            )
            
            if search_response.status_code == 200:
                print("搜索请求成功，解析结果...")
                return self.parse_search_results(search_response.text, max_results)
            else:
                print(f"搜索失败: {search_response.status_code}")
                return False
                
        except Exception as e:
            print(f"搜索过程中发生错误: {e}")
            return False
    
    def parse_search_results(self, html_content, max_results):
        """解析搜索结果"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找专利结果（根据CNKI的实际HTML结构调整）
            patent_items = soup.find_all('div', class_='result-item')
            
            if not patent_items:
                print("未找到专利结果，可能需要处理验证码或登录")
                # 尝试查找验证码相关信息
                captcha = soup.find('div', id='captcha')
                if captcha:
                    print("检测到验证码，需要人工干预")
                return False
            
            print(f"找到 {len(patent_items)} 条专利结果")
            
            for item in patent_items[:max_results]:
                patent_data = self.extract_patent_info(item)
                if patent_data:
                    self.results.append(patent_data)
            
            return True
            
        except Exception as e:
            print(f"解析结果时发生错误: {e}")
            return False
    
    def extract_patent_info(self, item):
        """提取单个专利信息"""
        try:
            # 专利标题
            title_elem = item.find('a', class_='title')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 专利链接
            link = title_elem['href'] if title_elem and title_elem.get('href') else ""
            if link and not link.startswith('http'):
                link = self.base_url + link
            
            # 发明人
            inventors_elem = item.find('span', class_='author')
            inventors = inventors_elem.get_text(strip=True) if inventors_elem else ""
            
            # 申请号/专利号
            patent_no_elem = item.find('span', class_='patent-no')
            patent_no = patent_no_elem.get_text(strip=True) if patent_no_elem else ""
            
            # 摘要
            abstract_elem = item.find('div', class_='abstract')
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            
            # 申请日期
            date_elem = item.find('span', class_='date')
            apply_date = date_elem.get_text(strip=True) if date_elem else ""
            
            patent_info = {
                'title': title,
                'link': link,
                'inventors': inventors,
                'patent_number': patent_no,
                'abstract': abstract,
                'apply_date': apply_date,
                'crawled_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"提取专利: {title}")
            return patent_info
            
        except Exception as e:
            print(f"提取专利信息时发生错误: {e}")
            return None
    
    def save_results(self, format='json'):
        """保存结果"""
        if not self.results:
            print("没有结果可保存")
            return False
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f"cnki_patents_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到 {filename}")
            
        elif format == 'csv':
            filename = f"cnki_patents_{timestamp}.csv"
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
            print(f"结果已保存到 {filename}")
            
        return filename
    
    def get_patent_detail(self, patent_url):
        """获取专利详细信息"""
        try:
            response = self.session.get(patent_url, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取详细信息（需要根据实际页面结构调整）
                detail_info = {
                    'full_text': soup.get_text(),
                    # 可以添加更多详细字段的提取逻辑
                }
                return detail_info
            
        except Exception as e:
            print(f"获取专利详情时发生错误: {e}")
            return None

def main():
    """主函数"""
    print("=== CNKI专利爬虫工具 ===")
    
    # 创建爬虫实例
    crawler = CNKIPatentCrawler()
    
    # 搜索关键词（可以根据需要修改）
    search_keywords = "人工智能"  # 示例关键词
    max_results = 20
    
    print(f"开始搜索关键词: {search_keywords}")
    
    # 执行搜索
    success = crawler.search_patents(search_keywords, max_results)
    
    if success and crawler.results:
        print(f"\n成功爬取 {len(crawler.results)} 条专利信息")
        
        # 显示前几条结果
        for i, patent in enumerate(crawler.results[:3], 1):
            print(f"\n{i}. {patent['title']}")
            print(f"   发明人: {patent['inventors']}")
            print(f"   专利号: {patent['patent_number']}")
        
        # 保存结果
        filename = crawler.save_results('json')
        print(f"\n详细结果已保存到: {filename}")
        
        # 同时保存CSV格式
        csv_filename = crawler.save_results('csv')
        print(f"CSV格式已保存到: {csv_filename}")
        
    else:
        print("爬取失败，可能的原因:")
        print("1. 需要验证码或登录")
        print("2. 网站结构发生变化")
        print("3. 网络连接问题")
        print("\n建议:")
        print("1. 手动访问 https://kns.cnki.net 完成验证")
        print("2. 如有账号，可能需要登录后才能搜索")

if __name__ == "__main__":
    main()