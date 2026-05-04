#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国知网(CNKI)专利爬虫工具 - 高级版
包含验证码处理和多策略爬取
"""

import requests
import time
import json
import csv
import re
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, urlencode

class CNKIPatentCrawlerAdvanced:
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
        self.search_urls = [
            "https://kns.cnki.net/kns8/AdvSearch",
            "https://kns.cnki.net/kns8/defaultresult/index",
            "https://kns.cnki.net/kns/brief/result.aspx"
        ]
        self.results = []
        self.cookies = {}
    
    def detect_captcha(self):
        """检测是否需要验证码"""
        try:
            test_url = "https://kns.cnki.net/kns8"
            response = self.session.get(test_url, timeout=10)
            
            if "安全验证" in response.text or "captcha" in response.text.lower():
                print("检测到验证码要求")
                return True
            return False
            
        except Exception as e:
            print(f"检测验证码时发生错误: {e}")
            return True
    
    def manual_captcha_solution(self):
        """手动处理验证码的指导"""
        print("\n=== 验证码处理指南 ===")
        print("1. 请手动访问: https://kns.cnki.net")
        print("2. 完成验证码验证")
        print("3. 复制浏览器中的Cookie信息")
        print("4. 将Cookie粘贴到这里")
        print("5. 或者使用已登录的会话")
        print("=====================\n")
        
        # 尝试获取用户输入的Cookie
        cookie_input = input("请输入Cookie字符串(格式: key1=value1; key2=value2): ")
        if cookie_input:
            self.parse_cookies(cookie_input)
            return True
        return False
    
    def parse_cookies(self, cookie_str):
        """解析Cookie字符串"""
        try:
            cookies = {}
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            self.cookies.update(cookies)
            self.session.cookies.update(cookies)
            print(f"已设置 {len(cookies)} 个Cookie")
            return True
            
        except Exception as e:
            print(f"解析Cookie时发生错误: {e}")
            return False
    
    def try_multiple_search_strategies(self, keywords, max_results=20):
        """尝试多种搜索策略"""
        strategies = [
            self.strategy_direct_search,
            self.strategy_advanced_search,
            self.strategy_simple_search
        ]
        
        for strategy in strategies:
            print(f"尝试策略: {strategy.__name__}")
            success = strategy(keywords, max_results)
            if success and self.results:
                print("策略成功!")
                return True
            time.sleep(2)  # 策略间延迟
        
        return False
    
    def strategy_direct_search(self, keywords, max_results):
        """直接搜索策略"""
        try:
            params = {
                'dbcode': 'SCPD',  # 专利数据库
                'kw': keywords,
                'page': 1,
                'size': min(max_results, 20)
            }
            
            response = self.session.post(
                "https://kns.cnki.net/kns8/defaultresult/index",
                data=params,
                timeout=30
            )
            
            return self.parse_search_response(response.text)
            
        except Exception as e:
            print(f"直接搜索策略失败: {e}")
            return False
    
    def strategy_advanced_search(self, keywords, max_results):
        """高级搜索策略"""
        try:
            # 先获取高级搜索页面
            response = self.session.get("https://kns.cnki.net/kns8/AdvSearch", timeout=30)
            
            if response.status_code != 200:
                return False
            
            # 提取必要的表单参数
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 构造高级搜索参数
            search_data = {
                'dbcode': 'SCPD',
                'txt_1_sel': 'SU',  # 主题
                'txt_1_value1': keywords,
                'txt_1_relation': '#CNKI_AND',
                'page': 1,
                'recordsperpage': min(max_results, 20)
            }
            
            search_response = self.session.post(
                "https://kns.cnki.net/kns8/AdvSearch",
                data=search_data,
                timeout=30
            )
            
            return self.parse_search_response(search_response.text)
            
        except Exception as e:
            print(f"高级搜索策略失败: {e}")
            return False
    
    def strategy_simple_search(self, keywords, max_results):
        """简单搜索策略"""
        try:
            encoded_keywords = quote(keywords)
            url = f"https://kns.cnki.net/kns/brief/result.aspx?dbprefix=SCPD&kw={encoded_keywords}"
            
            response = self.session.get(url, timeout=30)
            return self.parse_search_response(response.text)
            
        except Exception as e:
            print(f"简单搜索策略失败: {e}")
            return False
    
    def parse_search_response(self, html_content):
        """解析搜索响应"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 多种可能的选择器
            selectors = [
                'div.result-item',
                'tr[bgcolor="#ffffff"]',
                'div.wz_content',
                'div.list-item'
            ]
            
            patent_items = []
            for selector in selectors:
                patent_items = soup.select(selector)
                if patent_items:
                    break
            
            if not patent_items:
                print("未找到专利结果项")
                # 检查是否有错误信息
                error_msg = soup.find('div', class_='error')
                if error_msg:
                    print(f"错误信息: {error_msg.get_text()}")
                return False
            
            print(f"找到 {len(patent_items)} 个可能的结果项")
            
            for item in patent_items:
                patent_data = self.extract_patent_info(item)
                if patent_data:
                    self.results.append(patent_data)
            
            return len(self.results) > 0
            
        except Exception as e:
            print(f"解析搜索响应时发生错误: {e}")
            return False
    
    def extract_patent_info(self, item):
        """提取专利信息"""
        try:
            # 尝试多种标题选择器
            title = ""
            title_selectors = ['a.title', 'td[align="left"] a', 'h3 a', '.wz_tit a']
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            if not title:
                return None
            
            # 链接
            link = ""
            if title_elem and title_elem.get('href'):
                link = title_elem['href']
                if not link.startswith('http'):
                    link = urljoin(self.base_url, link)
            
            # 发明人
            inventors = ""
            inventor_selectors = ['.author', '.inventor', 'td[align="center"]']
            for selector in inventor_selectors:
                elem = item.select_one(selector)
                if elem:
                    inventors = elem.get_text(strip=True)
                    break
            
            # 专利号
            patent_no = ""
            patent_no_selectors = ['.patent-no', '.number', 'td:last-child']
            for selector in patent_no_selectors:
                elem = item.select_one(selector)
                if elem:
                    patent_no = elem.get_text(strip=True)
                    break
            
            patent_info = {
                'title': title,
                'link': link,
                'inventors': inventors,
                'patent_number': patent_no,
                'crawled_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"✓ 提取: {title}")
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
            filename = f"cnki_patents_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        elif format == 'csv':
            filename = f"cnki_patents_{timestamp}.csv"
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['title', 'link', 'inventors', 'patent_number', 'crawled_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        
        return filename
    
    def generate_report(self):
        """生成爬取报告"""
        report = {
            'total_patents': len(self.results),
            'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success' if self.results else 'failed',
            'results_sample': self.results[:3] if self.results else []
        }
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = f"crawl_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report_file

def main():
    """主函数"""
    print("=== CNKI专利爬虫工具 - 高级版 ===")
    print("专门处理中国知网的验证码和反爬机制")
    
    crawler = CNKIPatentCrawlerAdvanced()
    
    # 检测验证码
    if crawler.detect_captcha():
        print("需要处理验证码...")
        if not crawler.manual_captcha_solution():
            print("未提供Cookie，尝试无Cookie搜索...")
    
    # 搜索关键词
    search_keywords = "机器学习"  # 示例关键词
    max_results = 15
    
    print(f"\n开始搜索: {search_keywords}")
    
    # 尝试多种策略
    success = crawler.try_multiple_search_strategies(search_keywords, max_results)
    
    if success:
        print(f"\n✅ 成功爬取 {len(crawler.results)} 条专利")
        
        # 显示结果摘要
        print("\n=== 专利摘要 ===")
        for i, patent in enumerate(crawler.results[:5], 1):
            print(f"{i}. {patent['title']}")
            if patent['inventors']:
                print(f"   发明人: {patent['inventors']}")
            if patent['patent_number']:
                print(f"   专利号: {patent['patent_number']}")
            print()
        
        # 保存结果
        json_file = crawler.save_results('json')
        csv_file = crawler.save_results('csv')
        report_file = crawler.generate_report()
        
        print(f"📊 JSON数据: {json_file}")
        print(f"📋 CSV表格: {csv_file}")
        print(f"📝 爬取报告: {report_file}")
        
    else:
        print("\n❌ 所有策略都失败了")
        print("\n建议解决方案:")
        print("1. 手动访问 https://kns.cnki.net 完成验证")
        print("2. 登录CNKI账号获取搜索权限")
        print("3. 使用浏览器开发者工具复制Cookie")
        print("4. 考虑使用CNKI官方API(如果有权限)")
        
        # 生成失败报告
        report_file = crawler.generate_report()
        print(f"📝 失败报告: {report_file}")

if __name__ == "__main__":
    main()