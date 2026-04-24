#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国知网(CNKI)专利爬虫 - 支持登录版本
使用19525456@qq.com账号进行登录和专利爬取
"""

import requests
import time
import json
import csv
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, urlencode
import getpass

class CNKIPatentCrawlerWithLogin:
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
        self.login_url = "https://login.cnki.net/login"
        self.search_url = "https://kns.cnki.net/kns8/AdvSearch"
        self.results = []
        self.is_logged_in = False
    
    def manual_login_guide(self):
        """手动登录指导"""
        print("\n=== CNKI手动登录指南 ===")
        print("1. 请访问: https://login.cnki.net/login")
        print("2. 使用账号: 19525456@qq.com")
        print("3. 输入密码完成登录")
        print("4. 登录成功后访问: https://kns.cnki.net/kns8/AdvSearch")
        print("5. 按F12打开开发者工具")
        print("6. 转到Network标签页，刷新页面")
        print("7. 复制Cookie信息")
        print("8. 粘贴到下面的提示中")
        print("==========================\n")
        
        return True
    
    def get_cookie_from_user(self):
        """从用户获取Cookie"""
        try:
            print("请粘贴Cookie信息（格式: key1=value1; key2=value2）:")
            cookie_str = input("Cookie: ").strip()
            
            if not cookie_str:
                print("未提供Cookie")
                return False
            
            # 解析Cookie字符串
            cookies = {}
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            if not cookies:
                print("Cookie格式错误")
                return False
            
            # 更新session的cookies
            self.session.cookies.update(cookies)
            print(f"已设置 {len(cookies)} 个Cookie")
            
            # 验证登录状态
            return self.verify_login()
            
        except Exception as e:
            print(f"处理Cookie时发生错误: {e}")
            return False
    
    def verify_login(self):
        """验证登录状态"""
        try:
            test_url = "https://kns.cnki.net/kns8"
            response = self.session.get(test_url, timeout=10)
            
            # 检查登录状态
            if "退出" in response.text or "我的CNKI" in response.text:
                print("✅ 登录状态验证成功")
                self.is_logged_in = True
                return True
            elif "登录" in response.text or "请登录" in response.text:
                print("❌ 登录状态验证失败")
                return False
            else:
                print("⚠️  无法确定登录状态，继续尝试...")
                self.is_logged_in = True  # 假设登录成功
                return True
                
        except Exception as e:
            print(f"验证登录时发生错误: {e}")
            return False
    
    def search_patents(self, keywords, max_results=20):
        """搜索专利"""
        if not self.is_logged_in:
            print("请先完成登录")
            return False
        
        try:
            print(f"开始搜索专利: {keywords}")
            
            # 访问高级搜索页面
            response = self.session.get(self.search_url, timeout=30)
            if response.status_code != 200:
                print(f"无法访问搜索页面: {response.status_code}")
                return False
            
            # 提取搜索表单参数
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 构造搜索参数
            search_data = {
                'dbcode': 'SCPD',  # 专利数据库
                'txt_1_sel': 'SU',  # 主题字段
                'txt_1_value1': keywords,
                'txt_1_relation': '#CNKI_AND',
                'page': 1,
                'recordsperpage': min(max_results, 50),
                'displaymode': 'list',
                'sorttype': ''
            }
            
            # 执行搜索
            search_response = self.session.post(
                self.search_url,
                data=search_data,
                timeout=30,
                headers={'Referer': self.search_url}
            )
            
            if search_response.status_code == 200:
                print("搜索请求成功")
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
            
            # 查找专利结果 - 尝试多种选择器
            patent_items = []
            
            # 选择器1: 标准结果项
            patent_items = soup.select('div.result-item, tr[bgcolor="#ffffff"], .wz_content')
            
            # 选择器2: 表格行
            if not patent_items:
                patent_items = soup.select('tr')
            
            if not patent_items:
                print("未找到专利结果，可能页面结构变化")
                # 保存HTML用于调试
                with open('debug_search_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("已保存搜索页面HTML到 debug_search_page.html")
                return False
            
            print(f"找到 {len(patent_items)} 个结果项")
            
            count = 0
            for item in patent_items:
                if count >= max_results:
                    break
                
                patent_data = self.extract_patent_info(item)
                if patent_data:
                    self.results.append(patent_data)
                    count += 1
            
            print(f"成功提取 {len(self.results)} 条专利信息")
            return len(self.results) > 0
            
        except Exception as e:
            print(f"解析搜索结果时发生错误: {e}")
            return False
    
    def extract_patent_info(self, item):
        """提取专利信息"""
        try:
            # 转换为BeautifulSoup对象（如果是Tag则不需要）
            if not hasattr(item, 'find'):
                item = BeautifulSoup(str(item), 'html.parser')
            
            # 标题
            title = ""
            title_elem = item.find('a', class_='title')
            if not title_elem:
                title_elem = item.find('a', string=re.compile(r'.{10,}'))  # 包含一定长度的链接文本
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 5:  # 过滤掉太短的标题
                return None
            
            # 链接
            link = ""
            if title_elem and title_elem.get('href'):
                link = title_elem['href']
                if not link.startswith('http'):
                    link = urljoin(self.base_url, link)
            
            # 发明人
            inventors = ""
            inventor_elem = item.find('span', class_='author')
            if not inventor_elem:
                inventor_elem = item.find(string=re.compile(r'发明人[:：]'))
            if inventor_elem:
                inventors = inventor_elem.get_text(strip=True).replace('发明人：', '').replace('发明人:', '')
            
            # 专利号
            patent_no = ""
            patent_no_elem = item.find('span', class_='patent-no')
            if not patent_no_elem:
                patent_no_elem = item.find(string=re.compile(r'[A-Z]{2}\d+'))  # 匹配专利号格式
            if patent_no_elem:
                patent_no = patent_no_elem.get_text(strip=True)
            
            # 摘要（如果可用）
            abstract = ""
            abstract_elem = item.find('div', class_='abstract')
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)
            
            patent_info = {
                'title': title,
                'link': link,
                'inventors': inventors,
                'patent_number': patent_no,
                'abstract': abstract,
                'source': 'CNKI',
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
            filename = f"cnki_patents_with_login_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"JSON数据已保存到: {filename}")
            
        elif format == 'csv':
            filename = f"cnki_patents_with_login_{timestamp}.csv"
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['title', 'link', 'inventors', 'patent_number', 'abstract', 'source', 'crawled_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
            print(f"CSV数据已保存到: {filename}")
        
        return filename
    
    def generate_detailed_report(self):
        """生成详细报告"""
        report = {
            'total_patents': len(self.results),
            'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'login_status': self.is_logged_in,
            'account_used': '19525456@qq.com',
            'results_sample': self.results[:5] if self.results else [],
            'all_results_file': self.save_results('json')
        }
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = f"cnki_crawl_detailed_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"详细报告已保存到: {report_file}")
        return report_file

def main():
    """主函数"""
    print("=== CNKI专利爬虫 - 支持登录版本 ===")
    print("使用账号: 19525456@qq.com")
    
    crawler = CNKIPatentCrawlerWithLogin()
    
    # 显示登录指南
    crawler.manual_login_guide()
    
    # 获取Cookie并验证登录
    if crawler.get_cookie_from_user():
        print("✅ 登录成功!")
        
        # 搜索专利
        search_keywords = input("\n请输入要搜索的专利关键词: ").strip()
        if not search_keywords:
            search_keywords = "人工智能"  # 默认关键词
        
        max_results = 20
        success = crawler.search_patents(search_keywords, max_results)
        
        if success:
            print(f"\n🎉 成功爬取 {len(crawler.results)} 条专利!")
            
            # 显示结果摘要
            print("\n=== 专利摘要 ===")
            for i, patent in enumerate(crawler.results[:10], 1):
                print(f"{i}. {patent['title']}")
                if patent['inventors']:
                    print(f"   发明人: {patent['inventors']}")
                if patent['patent_number']:
                    print(f"   专利号: {patent['patent_number']}")
                print()
            
            # 保存结果
            json_file = crawler.save_results('json')
            csv_file = crawler.save_results('csv')
            report_file = crawler.generate_detailed_report()
            
            print(f"\n💾 数据文件:")
            print(f"   JSON: {json_file}")
            print(f"   CSV: {csv_file}")
            print(f"   报告: {report_file}")
            
        else:
            print("\n❌ 专利搜索失败")
            
    else:
        print("\n❌ 登录失败，请检查Cookie信息")

if __name__ == "__main__":
    main()