#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药大学获奖信息搜索脚本
用于搜索和整理全国中医药大学的获奖情况
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from urllib.parse import urljoin

class TCMUniversityAwardsSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.results = []
    
    def search_tcm_universities(self):
        """搜索主要中医药大学的获奖信息"""
        universities = [
            {
                'name': '北京中医药大学',
                'url': 'https://www.bucm.edu.cn/',
                'search_terms': ['获奖', '奖励', '成果奖', '教学成果', '科技奖']
            },
            {
                'name': '上海中医药大学', 
                'url': 'https://www.shutcm.edu.cn/',
                'search_terms': ['获奖', '奖励', '成果奖', '教学成果', '科技奖']
            },
            {
                'name': '广州中医药大学',
                'url': 'https://www.gzucm.edu.cn/',
                'search_terms': ['获奖', '奖励', '成果奖', '教学成果', '科技奖']
            },
            {
                'name': '南京中医药大学',
                'url': 'https://www.njucm.edu.cn/',
                'search_terms': ['获奖', '奖励', '成果奖', '教学成果', '科技奖']
            },
            {
                'name': '成都中医药大学',
                'url': 'https://www.cdutcm.edu.cn/',
                'search_terms': ['获奖', '奖励', '成果奖', '教学成果', '科技奖']
            }
        ]
        
        print("开始搜索中医药大学获奖信息...")
        
        for uni in universities:
            try:
                print(f"\n正在搜索 {uni['name']}...")
                self.search_university_awards(uni)
                time.sleep(2)  # 礼貌延迟
            except Exception as e:
                print(f"搜索 {uni['name']} 时出错: {e}")
    
    def search_university_awards(self, university):
        """搜索单个大学的获奖信息"""
        try:
            response = self.session.get(university['url'], timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找可能包含获奖信息的链接
                award_links = []
                for term in university['search_terms']:
                    links = soup.find_all('a', href=True, string=re.compile(term))
                    award_links.extend(links)
                
                # 去重
                award_links = list({link['href'] for link in award_links})
                
                print(f"在 {university['name']} 找到 {len(award_links)} 个相关链接")
                
                # 提取详细信息
                for link in award_links[:5]:  # 限制前5个链接
                    full_url = urljoin(university['url'], link)
                    self.extract_award_details(full_url, university['name'])
                    
            else:
                print(f"无法访问 {university['name']} 网站")
                
        except Exception as e:
            print(f"处理 {university['name']} 时出错: {e}")
    
    def extract_award_details(self, url, university_name):
        """提取获奖详细信息"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 提取标题
                title = soup.find('h1') or soup.find('title')
                title_text = title.get_text().strip() if title else '未知标题'
                
                # 提取正文内容
                content = soup.find('div', class_=re.compile(r'content|article|main'))
                content_text = content.get_text().strip() if content else ''
                
                # 查找获奖相关信息
                award_patterns = [
                    r'获奖.*[：:]([^。]+)',
                    r'奖励.*[：:]([^。]+)', 
                    r'成果奖.*[：:]([^。]+)',
                    r'教学成果.*[：:]([^。]+)',
                    r'科技奖.*[：:]([^。]+)'
                ]
                
                awards = []
                for pattern in award_patterns:
                    matches = re.findall(pattern, content_text)
                    awards.extend(matches)
                
                if awards:
                    award_info = {
                        'university': university_name,
                        'title': title_text,
                        'url': url,
                        'awards': awards,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.results.append(award_info)
                    print(f"发现获奖信息: {title_text}")
                    
        except Exception as e:
            print(f"提取 {url} 详情时出错: {e}")
    
    def save_results(self):
        """保存搜索结果"""
        if self.results:
            filename = f'tcm_university_awards_{time.strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"\n搜索结果已保存到 {filename}")
            
            # 生成简报告
            self.generate_report()
        else:
            print("未找到获奖信息")
    
    def generate_report(self):
        """生成搜索报告"""
        report = "# 中医药大学获奖信息搜索报告\n\n"
        report += f"搜索时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"找到 {len(self.results)} 条获奖信息\n\n"
        
        for result in self.results:
            report += f"## {result['university']}\n"
            report += f"**标题**: {result['title']}\n"
            report += f"**链接**: {result['url']}\n"
            report += "**获奖情况**:\n"
            for award in result['awards']:
                report += f"- {award}\n"
            report += "\n"
        
        report_filename = f'tcm_awards_report_{time.strftime("%Y%m%d_%H%M%S")}.md'
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"详细报告已保存到 {report_filename}")

def main():
    """主函数"""
    print("=" * 60)
    print("中医药大学获奖信息搜索系统")
    print("=" * 60)
    
    searcher = TCMUniversityAwardsSearcher()
    searcher.search_tcm_universities()
    searcher.save_results()
    
    print("\n搜索完成!")

if __name__ == "__main__":
    main()