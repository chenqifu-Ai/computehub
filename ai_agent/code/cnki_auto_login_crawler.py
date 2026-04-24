#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国知网(CNKI)自动登录爬虫
使用19525456@qq.com + c9fc9f,. 自动登录
"""

import requests
import time
import json
import csv
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode

class CNKIAutoLoginCrawler:
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
        
        # 账号信息
        self.username = "19525456@qq.com"
        self.password = "c9fc9f,."
    
    def auto_login(self):
        """自动登录CNKI"""
        try:
            print(f"尝试自动登录CNKI账号: {self.username}")
            
            # 首先获取登录页面，提取必要的参数
            print("获取登录页面...")
            login_page_response = self.session.get(self.login_url, timeout=30)
            
            if login_page_response.status_code != 200:
                print(f"无法访问登录页面: {login_page_response.status_code}")
                return False
            
            soup = BeautifulSoup(login_page_response.text, 'html.parser')
            
            # 查找登录表单和必要的隐藏字段
            form = soup.find('form', {'id': 'loginForm'})
            if not form:
                print("未找到登录表单")
                return False
            
            # 提取隐藏字段
            hidden_fields = {}
            for input_tag in form.find_all('input', {'type': 'hidden'}):
                if input_tag.get('name') and input_tag.get('value'):
                    hidden_fields[input_tag['name']] = input_tag['value']
            
            # 构造登录数据
            login_data = {
                'username': self.username,
                'password': self.password,
                'remember': 'true',
                **hidden_fields  # 包含所有隐藏字段
            }
            
            print("提交登录请求...")
            login_response = self.session.post(
                self.login_url,
                data=login_data,
                timeout=30,
                headers={
                    'Referer': self.login_url,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://login.cnki.net'
                }
            )
            
            # 检查登录是否成功
            if login_response.status_code == 200:
                # 检查响应中是否包含成功信息
                if "登录成功" in login_response.text or "我的CNKI" in login_response.text:
                    print("✅ 自动登录成功!")
                    self.is_logged_in = True
                    return True
                else:
                    print("❌ 登录可能失败，检查响应内容")
                    # 保存响应内容用于调试
                    with open('login_response.html', 'w', encoding='utf-8') as f:
                        f.write(login_response.text)
                    print("已保存登录响应到 login_response.html")
                    return False
            else:
                print(f"登录请求失败: {login_response.status_code}")
                return False
                
        except Exception as e:
            print(f"自动登录过程中发生错误: {e}")
            return False
    
    def manual_login_fallback(self):
        """手动登录备用方案"""
        print("\n=== 自动登录失败，启用手动登录方案 ===")
        print("请手动完成以下步骤:")
        print(f"1. 访问: {self.login_url}")
        print(f"2. 使用账号: {self.username}")
        print(f"3. 密码: {self.password}")
        print("4. 完成登录后访问: https://kns.cnki.net/kns8/AdvSearch")
        print("5. 按F12 → Network → 刷新页面")
        print("6. 复制Cookie信息并粘贴 below")
        print("============================================\n")
        
        try:
            cookie_str = input("请粘贴Cookie信息（格式: key1=value1; key2=value2）: ").strip()
            
            if not cookie_str:
                print("未提供Cookie")
                return False
            
            # 解析Cookie
            cookies = {}
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            if not cookies:
                print("Cookie格式错误")
                return False
            
            self.session.cookies.update(cookies)
            print(f"已设置 {len(cookies)} 个Cookie")
            
            # 验证登录状态
            return self.verify_login()
            
        except Exception as e:
            print(f"处理手动登录时发生错误: {e}")
            return False
    
    def verify_login(self):
        """验证登录状态"""
        try:
            test_url = "https://kns.cnki.net/kns8"
            response = self.session.get(test_url, timeout=10)
            
            if "退出" in response.text or "我的CNKI" in response.text:
                print("✅ 登录状态验证成功")
                self.is_logged_in = True
                return True
            elif "登录" in response.text or "请登录" in response.text:
                print("❌ 登录状态验证失败")
                return False
            else:
                print("⚠️  无法确定登录状态，继续尝试搜索...")
                self.is_logged_in = True
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
            print(f"搜索专利关键词: {keywords}")
            
            # 访问搜索页面
            response = self.session.get(self.search_url, timeout=30)
            if response.status_code != 200:
                print(f"无法访问搜索页面: {response.status_code}")
                return False
            
            # 尝试多种搜索策略
            strategies = [
                self._search_strategy1,
                self._search_strategy2,
                self._search_strategy3
            ]
            
            for strategy in strategies:
                print(f"尝试搜索策略: {strategy.__name__}")
                success = strategy(keywords, max_results)
                if success:
                    return True
                time.sleep(2)
            
            return False
                
        except Exception as e:
            print(f"搜索过程中发生错误: {e}")
            return False
    
    def _search_strategy1(self, keywords, max_results):
        """搜索策略1: 标准高级搜索"""
        try:
            search_data = {
                'dbcode': 'SCPD',
                'txt_1_sel': 'SU',
                'txt_1_value1': keywords,
                'txt_1_relation': '#CNKI_AND',
                'page': 1,
                'recordsperpage': min(max_results, 50),
            }
            
            response = self.session.post(
                self.search_url,
                data=search_data,
                timeout=30,
                headers={'Referer': self.search_url}
            )
            
            if response.status_code == 200:
                return self.parse_search_results(response.text, max_results)
            return False
            
        except Exception as e:
            print(f"策略1失败: {e}")
            return False
    
    def _search_strategy2(self, keywords, max_results):
        """搜索策略2: 简单搜索"""
        try:
            encoded_keywords = requests.utils.quote(keywords)
            url = f"https://kns.cnki.net/kns/brief/result.aspx?dbprefix=SCPD&kw={encoded_keywords}"
            
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return self.parse_search_results(response.text, max_results)
            return False
            
        except Exception as e:
            print(f"策略2失败: {e}")
            return False
    
    def _search_strategy3(self, keywords, max_results):
        """搜索策略3: 默认结果页面"""
        try:
            params = {
                'dbcode': 'SCPD',
                'kw': keywords,
                'page': 1,
                'size': min(max_results, 20)
            }
            
            response = self.session.post(
                "https://kns.cnki.net/kns8/defaultresult/index",
                data=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return self.parse_search_results(response.text, max_results)
            return False
            
        except Exception as e:
            print(f"策略3失败: {e}")
            return False
    
    def parse_search_results(self, html_content, max_results):
        """解析搜索结果"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 多种可能的选择器
            selectors = [
                'div.result-item',
                'tr[bgcolor="#ffffff"]',
                '.wz_content',
                '.list-item',
                'tr'
            ]
            
            patent_items = []
            for selector in selectors:
                patent_items = soup.select(selector)
                if patent_items:
                    break
            
            if not patent_items:
                print("未找到专利结果")
                # 保存页面用于调试
                with open('search_results_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("已保存搜索结果页面到 search_results_debug.html")
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
            
            print(f"成功提取 {len(self.results)} 条专利")
            return len(self.results) > 0
            
        except Exception as e:
            print(f"解析结果时发生错误: {e}")
            return False
    
    def extract_patent_info(self, item):
        """提取专利信息"""
        try:
            if not hasattr(item, 'find'):
                item = BeautifulSoup(str(item), 'html.parser')
            
            # 标题
            title = ""
            title_selectors = ['a.title', 'td[align="left"] a', 'h3 a', 'a']
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    break
            
            if not title or len(title) < 5:
                return None
            
            # 链接
            link = ""
            if title_elem and title_elem.get('href'):
                link = title_elem['href']
                if not link.startswith('http'):
                    link = urljoin(self.base_url, link)
            
            patent_info = {
                'title': title,
                'link': link,
                'source': 'CNKI',
                'crawled_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"✓ {title}")
            return patent_info
            
        except Exception as e:
            print(f"提取信息时发生错误: {e}")
            return None
    
    def save_results(self, format='json'):
        """保存结果"""
        if not self.results:
            print("没有结果可保存")
            return None
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f"cnki_patents_auto_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        elif format == 'csv':
            filename = f"cnki_patents_auto_{timestamp}.csv"
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['title', 'link', 'source', 'crawled_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        
        return filename

def main():
    """主函数"""
    print("=== CNKI自动登录专利爬虫 ===")
    print("使用账号: 19525456@qq.com")
    
    crawler = CNKIAutoLoginCrawler()
    
    # 尝试自动登录
    if crawler.auto_login():
        print("✅ 自动登录成功!")
    else:
        print("❌ 自动登录失败，启用手动方案")
        if not crawler.manual_login_fallback():
            print("❌ 所有登录方式都失败")
            return
    
    # 搜索专利
    search_keywords = "人工智能"  # 默认搜索词
    max_results = 15
    
    print(f"\n开始搜索: {search_keywords}")
    
    success = crawler.search_patents(search_keywords, max_results)
    
    if success:
        print(f"\n🎉 成功爬取 {len(crawler.results)} 条专利!")
        
        # 显示结果
        print("\n=== 专利列表 ===")
        for i, patent in enumerate(crawler.results, 1):
            print(f"{i}. {patent['title']}")
            print(f"   链接: {patent['link']}")
            print()
        
        # 保存结果
        json_file = crawler.save_results('json')
        csv_file = crawler.save_results('csv')
        
        print(f"💾 数据文件:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")
        
    else:
        print("\n❌ 专利搜索失败")

if __name__ == "__main__":
    main()