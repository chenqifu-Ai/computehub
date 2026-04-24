#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药建模比赛数据搜索脚本
用于自动化搜索中医药大学建模比赛获奖信息
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from urllib.parse import quote

# 中医药大学列表
TCM_UNIVERSITIES = [
    "北京中医药大学",
    "上海中医药大学", 
    "广州中医药大学",
    "南京中医药大学",
    "成都中医药大学",
    "天津中医药大学",
    "浙江中医药大学",
    "山东中医药大学",
    "湖南中医药大学",
    "湖北中医药大学"
]

# 搜索关键词
SEARCH_KEYWORDS = [
    "数学建模 获奖",
    "建模比赛 一等奖", 
    "全国大学生数学建模",
    "美赛 获奖",
    "数学建模竞赛",
    "AI 中医药 模型",
    "机器学习 中医",
    "数据挖掘 中医药"
]

# 各大学官网搜索URL模板
UNIVERSITY_SEARCH_URLS = {
    "北京中医药大学": "https://www.bucm.edu.cn/search?q={}",
    "上海中医药大学": "https://www.shutcm.edu.cn/search?q={}",
    "广州中医药大学": "https://www.gzucm.edu.cn/search?q={}",
    "南京中医药大学": "https://www.njucm.edu.cn/search?q={}",
    "成都中医药大学": "https://www.cdutcm.edu.cn/search?q={}"
}

def search_university_news(university, keyword):
    """搜索大学官网新闻"""
    try:
        if university in UNIVERSITY_SEARCH_URLS:
            url = UNIVERSITY_SEARCH_URLS[university].format(quote(keyword))
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # 提取搜索结果
                results = []
                for item in soup.find_all(['a', 'div'], class_=re.compile(r'(news|result|item)')):
                    title = item.get_text(strip=True)
                    link = item.get('href')
                    if title and link and keyword in title:
                        results.append({
                            'university': university,
                            'title': title,
                            'link': link if link.startswith('http') else f"https://www.{university}.edu.cn{link}",
                            'keyword': keyword
                        })
                return results
        return []
    except Exception as e:
        print(f"搜索{university}时出错: {e}")
        return []

def main():
    """主函数"""
    all_results = []
    
    print("开始搜索中医药大学建模比赛信息...")
    
    for university in TCM_UNIVERSITIES:
        print(f"正在搜索: {university}")
        
        for keyword in SEARCH_KEYWORDS:
            results = search_university_news(university, keyword)
            all_results.extend(results)
            time.sleep(1)  # 避免请求过于频繁
    
    # 保存结果
    if all_results:
        with open('tcm_modeling_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"找到 {len(all_results)} 条相关结果，已保存到 tcm_modeling_results.json")
    else:
        print("未找到相关结果")

if __name__ == "__main__":
    main()