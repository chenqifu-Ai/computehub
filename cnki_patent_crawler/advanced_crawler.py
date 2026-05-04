# 高级爬虫 - 处理知网反爬机制
import requests
import time
import random
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from config import BASE_URL, SEARCH_KEYWORDS, USER_AGENTS

class AdvancedCNKICrawler:
    def __init__(self):
        self.session = requests.Session()
        self.patents_data = []
        self.cookies = {}
        
    def get_headers(self):
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
    
    def make_safe_request(self, url, max_retries=3):
        """安全的请求函数"""
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(2, 4))
                headers = self.get_headers()
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    cookies=self.cookies
                )
                
                if response.status_code == 200:
                    # 更新cookies
                    self.cookies.update(response.cookies.get_dict())
                    return response
                elif response.status_code == 403:
                    print("遇到反爬限制，等待重试...")
                    time.sleep(10)
                else:
                    print(f"HTTP {response.status_code}, 重试中...")
                    
            except Exception as e:
                print(f"请求错误: {e}, 重试 {attempt + 1}/{max_retries}")
                time.sleep(5)
        
        return None
    
    def search_patents_api(self, keyword, page=1):
        """使用API方式搜索专利"""
        # 构建搜索参数
        search_params = {
            'kw': keyword,
            'db': 'SCPD',
            'page': page,
            'size': 20,
            'sort': 'relevance'
        }
        
        # API端点（可能需要动态获取）
        api_url = f"{BASE_URL}/kns8/api/search"
        
        response = self.make_safe_request(api_url, params=search_params)
        if response and response.json():
            return response.json()
        return None
    
    def parse_patent_from_api(self, patent_json):
        """从API响应解析专利数据"""
        try:
            return {
                'title': patent_json.get('Title', ''),
                'patent_number': patent_json.get('PatentNumber', ''),
                'applicant': patent_json.get('Applicant', ''),
                'inventor': patent_json.get('Inventor', ''),
                'application_date': patent_json.get('ApplicationDate', ''),
                'abstract': patent_json.get('Abstract', ''),
                'publication_date': patent_json.get('PublicationDate', ''),
                'ipc_class': patent_json.get('IPC', ''),
                'source': 'CNKI'
            }
        except Exception as e:
            print(f"解析API数据错误: {e}")
            return None
    
    def crawl_by_keywords(self, max_patents=100):
        """按关键词爬取"""
        print("开始高级爬取模式...")
        
        for keyword in SEARCH_KEYWORDS:
            print(f"\n搜索关键词: {keyword}")
            
            page = 1
            while len(self.patents_data) < max_patents:
                print(f"获取第 {page} 页...")
                
                # 尝试API方式
                data = self.search_patents_api(keyword, page)
                if not data:
                    print(f"第 {page} 页获取失败")
                    break
                
                patents = data.get('data', [])
                if not patents:
                    print("没有更多数据")
                    break
                
                for patent_json in patents:
                    patent = self.parse_patent_from_api(patent_json)
                    if patent:
                        self.patents_data.append(patent)
                        print(f"获取专利: {patent['title'][:50]}...")
                
                if len(patents) < 20:  # 最后一页
                    break
                
                page += 1
                time.sleep(random.uniform(3, 6))
                
                if len(self.patents_data) >= max_patents:
                    break
        
        print(f"\n爬取完成! 总共获取 {len(self.patents_data)} 条专利")
        
    def save_data(self):
        """保存数据"""
        if not self.patents_data:
            print("没有数据可保存")
            return
        
        # 去重
        unique_patents = {}
        for patent in self.patents_data:
            key = patent.get('patent_number') or patent.get('title')
            if key:
                unique_patents[key] = patent
        
        self.patents_data = list(unique_patents.values())
        
        # 保存JSON
        with open('cnki_patents.json', 'w', encoding='utf-8') as f:
            json.dump(self.patents_data, f, ensure_ascii=False, indent=2)
        
        # 保存CSV
        df = pd.DataFrame(self.patents_data)
        df.to_csv('cnki_patents.csv', index=False, encoding='utf-8-sig')
        
        print(f"数据已保存: {len(self.patents_data)} 条唯一专利")
        
    def run(self):
        """运行爬虫"""
        try:
            self.crawl_by_keywords(max_patents=50)
            self.save_data()
            return self.patents_data
        except Exception as e:
            print(f"爬虫运行错误: {e}")
            return []

# 测试函数
def test_crawler():
    """测试爬虫"""
    crawler = AdvancedCNKICrawler()
    
    # 先测试一个简单的请求
    test_url = "https://kns.cnki.net"
    response = crawler.make_safe_request(test_url)
    
    if response:
        print("连接测试成功")
        # 运行完整爬取
        return crawler.run()
    else:
        print("连接测试失败")
        return []

if __name__ == "__main__":
    test_crawler()