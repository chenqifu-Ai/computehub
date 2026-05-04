# 爬虫配置
import random

# 请求配置
REQUEST_DELAY = random.uniform(2, 5)  # 随机延迟2-5秒
MAX_RETRIES = 3
TIMEOUT = 30

# 搜索关键词
SEARCH_KEYWORDS = [
    "人工智能", "AI", "Artificial Intelligence",
    "机器学习", "Machine Learning", 
    "深度学习", "Deep Learning",
    "神经网络", "Neural Network",
    "计算机视觉", "Computer Vision",
    "自然语言处理", "NLP"
]

# 输出配置
OUTPUT_JSON = "patents_data.json"
OUTPUT_CSV = "patents_data.csv"

# User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# 知网URL
BASE_URL = "https://kns.cnki.net"
SEARCH_URL = "https://kns.cnki.net/kns8/AdvSearch"
PATENT_DB = "SCPD"  # 专利数据库