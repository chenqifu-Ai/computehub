# 主程序
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler import CNKIPatentCrawler
from config import SEARCH_KEYWORDS
import time

def main():
    print("=" * 50)
    print("中国知网专利数据爬虫")
    print("=" * 50)
    print(f"搜索关键词: {', '.join(SEARCH_KEYWORDS)}")
    print()
    
    # 创建爬虫实例
    crawler = CNKIPatentCrawler()
    
    try:
        # 执行爬取
        start_time = time.time()
        patents_data = crawler.run_search()
        end_time = time.time()
        
        print(f"\n爬取完成!")
        print(f"总耗时: {end_time - start_time:.2f} 秒")
        print(f"获取专利数量: {len(patents_data)}")
        
        # 显示统计信息
        if patents_data:
            print("\n专利统计:")
            print(f"- 包含摘要的专利: {sum(1 for p in patents_data if p.get('abstract'))}")
            print(f"- 包含发明人的专利: {sum(1 for p in patents_data if p.get('inventor'))}")
            print(f"- 包含申请日期的专利: {sum(1 for p in patents_data if p.get('application_date'))}")
        
    except KeyboardInterrupt:
        print("\n用户中断爬取")
        if crawler.patents_data:
            crawler.save_data()
            print("已保存已收集的数据")
    except Exception as e:
        print(f"\n爬取过程中发生错误: {e}")
        if crawler.patents_data:
            crawler.save_data()
            print("已保存已收集的数据")

if __name__ == "__main__":
    main()