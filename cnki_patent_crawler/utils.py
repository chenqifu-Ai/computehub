# 工具函数
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from config import REQUEST_DELAY, MAX_RETRIES, TIMEOUT, USER_AGENTS

def get_random_headers():
    """获取随机请求头"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def make_request(url, headers=None, retries=MAX_RETRIES):
    """发送HTTP请求"""
    if headers is None:
        headers = get_random_headers()
    
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"请求失败 (尝试 {attempt + 1}/{retries}): {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避
    return None

def parse_html(html_content):
    """解析HTML内容"""
    return BeautifulSoup(html_content, 'html.parser')

def extract_text(element, default=""):
    """安全提取文本"""
    if element:
        return element.get_text(strip=True)
    return default

def clean_text(text):
    """清理文本"""
    if text:
        return ' '.join(text.split())  # 去除多余空白
    return ""

def validate_patent_data(patent):
    """验证专利数据完整性"""
    required_fields = ['title', 'patent_number', 'applicant']
    return all(patent.get(field) for field in required_fields)