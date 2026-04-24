#!/usr/bin/env python3
# 知网专利爬虫执行脚本

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime

def create_sample_data():
    """创建示例数据（用于测试）"""
    sample_patents = [
        {
            "title": "基于深度学习的人工智能图像识别方法",
            "patent_number": "CN202310123456.7",
            "applicant": "清华大学",
            "inventor": "张三; 李四; 王五",
            "application_date": "2023-01-15",
            "abstract": "本发明涉及一种基于深度学习的人工智能图像识别方法，通过卷积神经网络实现高效图像分类。",
            "publication_date": "2023-06-20",
            "ipc_class": "G06V10/82",
            "source": "CNKI"
        },
        {
            "title": "机器学习驱动的智能推荐系统",
            "patent_number": "CN202310654321.2",
            "applicant": "阿里巴巴集团",
            "inventor": "赵六; 钱七",
            "application_date": "2023-02-28",
            "abstract": "一种基于机器学习算法的智能商品推荐系统，提高电商平台用户体验。",
            "publication_date": "2023-07-15",
            "ipc_class": "G06Q30/06",
            "source": "CNKI"
        },
        {
            "title": "神经网络在自然语言处理中的应用",
            "patent_number": "CN202310987654.1",
            "applicant": "百度在线网络技术有限公司",
            "inventor": "孙八; 周九",
            "application_date": "2023-03-10",
            "abstract": "本发明公开了神经网络在自然语言处理领域的创新应用方法。",
            "publication_date": "2023-08-05",
            "ipc_class": "G06F40/279",
            "source": "CNKI"
        },
        {
            "title": "计算机视觉辅助的工业检测系统",
            "patent_number": "CN202311234567.8",
            "applicant": "华为技术有限公司",
            "inventor": "吴十; 郑十一",
            "application_date": "2023-04-05",
            "abstract": "基于计算机视觉技术的工业产品质量自动检测系统。",
            "publication_date": "2023-09-10",
            "ipc_class": "G01N21/88",
            "source": "CNKI"
        },
        {
            "title": "深度学习模型优化方法及装置",
            "patent_number": "CN202311765432.9",
            "applicant": "腾讯科技（深圳）有限公司",
            "inventor": "王十二; 陈十三",
            "application_date": "2023-05-20",
            "abstract": "一种深度学习模型训练优化方法，提高模型收敛速度和准确率。",
            "publication_date": "2023-10-15",
            "ipc_class": "G06N3/08",
            "source": "CNKI"
        }
    ]
    
    return sample_patents

def save_data(patents_data, format='both'):
    """保存数据到文件"""
    if not patents_data:
        print("没有数据可保存")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        if format in ['json', 'both']:
            json_file = f"cnki_patents_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(patents_data, f, ensure_ascii=False, indent=2)
            print(f"JSON数据已保存: {json_file}")
        
        if format in ['csv', 'both']:
            csv_file = f"cnki_patents_{timestamp}.csv"
            df = pd.DataFrame(patents_data)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"CSV数据已保存: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"保存数据时出错: {e}")
        return False

def generate_report(patents_data):
    """生成数据报告"""
    if not patents_data:
        return "没有数据"
    
    report = {
        "total_patents": len(patents_data),
        "with_abstract": sum(1 for p in patents_data if p.get('abstract')),
        "with_inventor": sum(1 for p in patents_data if p.get('inventor')),
        "with_date": sum(1 for p in patents_data if p.get('application_date')),
        "applicants": {},
        "keywords_count": {}
    }
    
    # 统计申请人
    for patent in patents_data:
        applicant = patent.get('applicant', '未知')
        report['applicants'][applicant] = report['applicants'].get(applicant, 0) + 1
    
    # 关键词统计
    keywords = ['人工智能', '机器学习', '深度学习', '神经网络', '计算机视觉', '自然语言处理']
    for patent in patents_data:
        title = patent.get('title', '').lower()
        for keyword in keywords:
            if keyword.lower() in title:
                report['keywords_count'][keyword] = report['keywords_count'].get(keyword, 0) + 1
    
    return report

def main():
    """主函数"""
    print("=" * 60)
    print("中国知网专利数据采集系统")
    print("=" * 60)
    print("注意: 由于知网反爬机制，实际爬取可能需要验证码处理")
    print("当前生成示例数据用于演示")
    print()
    
    # 生成示例数据
    print("生成示例专利数据...")
    patents_data = create_sample_data()
    
    # 保存数据
    print("保存数据文件...")
    success = save_data(patents_data)
    
    if success:
        # 生成报告
        report = generate_report(patents_data)
        
        print("\n数据采集报告:")
        print(f"总专利数: {report['total_patents']}")
        print(f"包含摘要: {report['with_abstract']}")
        print(f"包含发明人: {report['with_inventor']}")
        print(f"包含日期: {report['with_date']}")
        
        print("\n申请人分布:")
        for applicant, count in report['applicants'].items():
            print(f"  {applicant}: {count}")
        
        print("\n关键词出现次数:")
        for keyword, count in report['keywords_count'].items():
            print(f"  {keyword}: {count}")
        
        print("\n采集完成! 数据文件已保存到当前目录")
        
        # 提示邮件发送
        print("\n如需发送邮件，请配置 email_sender.py 中的邮箱信息")
        print("接收邮箱: 19525456@qq.com")
        
    else:
        print("数据保存失败")

if __name__ == "__main__":
    main()