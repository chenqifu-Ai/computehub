# 主爬虫类
import time
import json
import pandas as pd
from bs4 import BeautifulSoup
from utils import make_request, parse_html, extract_text, clean_text, validate_patent_data
from config import BASE_URL, SEARCH_URL, PATENT_DB, SEARCH_KEYWORDS

class CNKIPatentCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.patents_data = []
        self.search_params = {
            'dbprefix': PATENT_DB,
            'action': '',
            'NaviCode': '*',
            'ua': '1.21',
            'PageName': 'ASP.brief_default_result_aspx',
            'isinEn': '0',
            ''
        }
    
    def build_search_url(self, keyword, page=1):
        """构建搜索URL"""
        params = self.search_params.copy()
        params['txt_1_value1'] = keyword
        params['txt_1_sel'] = 'DE'  # 题名
        params['txt_1_special1'] = '%'
        params['page'] = page
        
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f"{SEARCH_URL}?{query_string}"
    
    def search_patents(self, keyword, max_pages=5):
        """搜索专利"""
        print(f"开始搜索关键词: {keyword}")
        
        for page in range(1, max_pages + 1):
            try:
                search_url = self.build_search_url(keyword, page)
                print(f"正在获取第 {page} 页: {search_url}")
                
                response = make_request(search_url)
                if not response:
                    continue
                
                soup = parse_html(response.text)
                
                # 解析专利列表
                patent_items = soup.select('.result-table-list tbody tr')
                if not patent_items:
                    print(f"第 {page} 页没有找到专利结果")
                    break
                
                print(f"第 {page} 页找到 {len(patent_items)} 条专利")
                
                for item in patent_items:
                    patent_info = self.parse_patent_item(item)
                    if patent_info:
                        self.patents_data.append(patent_info)
                
                # 检查是否有下一页
                next_page = soup.select_one('.next')
                if not next_page or 'disabled' in next_page.get('class', []):
                    break
                
                time.sleep(2)  # 页面间延迟
                
            except Exception as e:
                print(f"搜索第 {page} 页时出错: {e}")
                continue
    
    def parse_patent_item(self, item):
        """解析专利列表项"""
        try:
            # 提取基本信息
            title_elem = item.select_one('.name a')
            patent_number_elem = item.select_one('.patent-number')
            applicant_elem = item.select_one('.applicant')
            inventor_elem = item.select_one('.inventor')
            date_elem = item.select_one('.date')
            
            patent = {
                'title': extract_text(title_elem),
                'patent_number': extract_text(patent_number_elem),
                'applicant': extract_text(applicant_elem),
                'inventor': extract_text(inventor_elem),
                'application_date': extract_text(date_elem),
                'abstract': '',  # 需要在详情页获取
                'detail_url': title_elem.get('href') if title_elem else ''
            }
            
            # 获取详情页信息
            if patent['detail_url']:
                detail_info = self.get_patent_detail(patent['detail_url'])
                patent.update(detail_info)
            
            return patent if validate_patent_data(patent) else None
            
        except Exception as e:
            print(f"解析专利项时出错: {e}")
            return None
    
    def get_patent_detail(self, detail_url):
        """获取专利详情信息"""
        try:
            full_url = BASE_URL + detail_url if detail_url.startswith('/') else detail_url
            response = make_request(full_url)
            if not response:
                return {}
            
            soup = parse_html(response.text)
            
            # 提取摘要和其他详细信息
            abstract_elem = soup.select_one('.abstract-text')
            
            detail_info = {
                'abstract': extract_text(abstract_elem),
                # 可以添加更多详细信息字段
            }
            
            return detail_info
            
        except Exception as e:
            print(f"获取专利详情时出错: {e}")
            return {}
    
    def run_search(self):
        """执行搜索任务"""
        print("开始执行知网专利搜索任务...")
        
        for keyword in SEARCH_KEYWORDS:
            self.search_patents(keyword)
            time.sleep(5)  # 关键词间延迟
        
        print(f"总共收集到 {len(self.patents_data)} 条专利数据")
        
        # 保存数据
        self.save_data()
        
        return self.patents_data
    
    def save_data(self):
        """保存数据到文件"""
        if not self.patents_data:
            print("没有数据可保存")
            return
        
        # 保存为JSON
        with open('patents_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.patents_data, f, ensure_ascii=False, indent=2)
        
        # 保存为CSV
        df = pd.DataFrame(self.patents_data)
        df.to_csv('patents_data.csv', index=False, encoding='utf-8-sig')
        
        print(f"数据已保存到 patents_data.json 和 patents_data.csv")

if __name__ == "__main__":
    crawler = CNKIPatentCrawler()
    crawler.run_search()