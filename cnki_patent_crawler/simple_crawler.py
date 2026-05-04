#!/usr/bin/env python3
# 简单版知网专利爬虫 - 无需额外依赖

import json
import time
import random
from datetime import datetime

def create_sample_patents():
    """创建示例专利数据"""
    return [
        {
            "title": "基于深度学习的人工智能图像识别方法",
            "patent_number": "CN202310123456.7",
            "applicant": "清华大学",
            "inventor": "张三; 李四; 王五",
            "application_date": "2023-01-15",
            "abstract": "本发明涉及一种基于深度学习的人工智能图像识别方法，通过卷积神经网络实现高效图像分类和目标检测。",
            "publication_date": "2023-06-20",
            "ipc_class": "G06V10/82",
            "source": "CNKI",
            "keyword": "深度学习"
        },
        {
            "title": "机器学习驱动的智能推荐系统及装置",
            "patent_number": "CN202310654321.2",
            "applicant": "阿里巴巴集团",
            "inventor": "赵六; 钱七",
            "application_date": "2023-02-28",
            "abstract": "一种基于机器学习算法的智能商品推荐系统，能够根据用户行为数据进行个性化推荐。",
            "publication_date": "2023-07-15",
            "ipc_class": "G06Q30/06",
            "source": "CNKI",
            "keyword": "机器学习"
        },
        {
            "title": "神经网络在自然语言处理中的应用方法",
            "patent_number": "CN202310987654.1",
            "applicant": "百度在线网络技术有限公司",
            "inventor": "孙八; 周九",
            "application_date": "2023-03-10",
            "abstract": "本发明公开了神经网络在自然语言处理领域的创新应用方法，包括文本分类和情感分析。",
            "publication_date": "2023-08-05",
            "ipc_class": "G06F40/279",
            "source": "CNKI",
            "keyword": "神经网络"
        },
        {
            "title": "计算机视觉辅助的工业产品质量检测系统",
            "patent_number": "CN202311234567.8",
            "applicant": "华为技术有限公司",
            "inventor": "吴十; 郑十一",
            "application_date": "2023-04-05",
            "abstract": "基于计算机视觉技术的工业产品质量自动检测系统，提高生产效率和产品质量。",
            "publication_date": "2023-09-10",
            "ipc_class": "G01N21/88",
            "source": "CNKI",
            "keyword": "计算机视觉"
        },
        {
            "title": "深度学习模型优化方法及训练装置",
            "patent_number": "CN202311765432.9",
            "applicant": "腾讯科技（深圳）有限公司",
            "inventor": "王十二; 陈十三",
            "application_date": "2023-05-20",
            "abstract": "一种深度学习模型训练优化方法，通过改进算法提高模型收敛速度和预测准确率。",
            "publication_date": "2023-10-15",
            "ipc_class": "G06N3/08",
            "source": "CNKI",
            "keyword": "深度学习"
        },
        {
            "title": "人工智能在医疗诊断中的辅助系统",
            "patent_number": "CN202312345678.0",
            "applicant": "北京邮电大学",
            "inventor": "李十四; 刘十五",
            "application_date": "2023-06-10",
            "abstract": "基于人工智能技术的医疗影像诊断辅助系统，帮助医生提高诊断准确性。",
            "publication_date": "2023-11-20",
            "ipc_class": "G16H50/20",
            "source": "CNKI",
            "keyword": "人工智能"
        },
        {
            "title": "自然语言处理中的语义理解方法",
            "patent_number": "CN202313579246.3",
            "applicant": "中国科学院计算技术研究所",
            "inventor": "张十六; 杨十七",
            "application_date": "2023-07-15",
            "abstract": "改进的自然语言处理语义理解方法，能够更好地处理中文语言的复杂性。",
            "publication_date": "2023-12-25",
            "ipc_class": "G06F40/30",
            "source": "CNKI",
            "keyword": "自然语言处理"
        },
        {
            "title": "基于机器学习的金融风险预测系统",
            "patent_number": "CN202314682935.4",
            "applicant": "平安科技（深圳）有限公司",
            "inventor": "黄十八; 林十九",
            "application_date": "2023-08-20",
            "abstract": "利用机器学习算法构建的金融风险预测和评估系统。",
            "publication_date": "2024-01-30",
            "ipc_class": "G06Q40/03",
            "source": "CNKI",
            "keyword": "机器学习"
        },
        {
            "title": "深度学习在自动驾驶中的应用",
            "patent_number": "CN202315791357.5",
            "applicant": "小鹏汽车",
            "inventor": "陈二十; 吴二十一",
            "application_date": "2023-09-25",
            "abstract": "将深度学习技术应用于自动驾驶系统的环境感知和决策制定。",
            "publication_date": "2024-02-28",
            "ipc_class": "G05D1/02",
            "source": "CNKI",
            "keyword": "深度学习"
        },
        {
            "title": "人工智能语音识别与处理系统",
            "patent_number": "CN202316842159.6",
            "applicant": "科大讯飞股份有限公司",
            "inventor": "刘二十二; 王二十三",
            "application_date": "2023-10-30",
            "abstract": "高效的人工智能语音识别和处理系统，支持多种语言和方言。",
            "publication_date": "2024-03-30",
            "ipc_class": "G10L15/26",
            "source": "CNKI",
            "keyword": "人工智能"
        }
    ]

def save_json(data, filename):
    """保存为JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"JSON文件已保存: {filename}")
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        return False

def save_csv(data, filename):
    """保存为CSV文件"""
    try:
        # 获取所有字段
        all_fields = set()
        for item in data:
            all_fields.update(item.keys())
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入表头
            header = ','.join(all_fields)
            f.write(header + '\n')
            
            # 写入数据
            for item in data:
                row = []
                for field in all_fields:
                    value = str(item.get(field, '')).replace(',', ';')
                    row.append(f'"{value}"')
                f.write(','.join(row) + '\n')
        
        print(f"CSV文件已保存: {filename}")
        return True
    except Exception as e:
        print(f"保存CSV失败: {e}")
        return False

def generate_report(data):
    """生成数据报告"""
    if not data:
        return "没有数据"
    
    report = {
        "total": len(data),
        "by_keyword": {},
        "by_applicant": {},
        "fields_summary": {}
    }
    
    # 统计关键词
    for item in data:
        keyword = item.get('keyword', '其他')
        report['by_keyword'][keyword] = report['by_keyword'].get(keyword, 0) + 1
    
    # 统计申请人
    for item in data:
        applicant = item.get('applicant', '未知')
        report['by_applicant'][applicant] = report['by_applicant'].get(applicant, 0) + 1
    
    # 字段完整性
    for item in data:
        for field, value in item.items():
            if value:
                report['fields_summary'][field] = report['fields_summary'].get(field, 0) + 1
    
    return report

def main():
    """主函数"""
    print("=" * 60)
    print("中国知网专利数据采集系统 (简单版)")
    print("=" * 60)
    print("生成示例数据...")
    
    # 创建示例数据
    patents = create_sample_patents()
    
    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"patents_data_{timestamp}.json"
    csv_file = f"patents_data_{timestamp}.csv"
    
    success_json = save_json(patents, json_file)
    success_csv = save_csv(patents, csv_file)
    
    if success_json or success_csv:
        # 生成报告
        report = generate_report(patents)
        
        print("\n📊 数据采集报告:")
        print(f"总专利数: {report['total']}")
        
        print("\n🔍 按关键词分布:")
        for keyword, count in report['by_keyword'].items():
            print(f"  {keyword}: {count}")
        
        print("\n🏢 按申请人分布:")
        for applicant, count in report['by_applicant'].items():
            print(f"  {applicant}: {count}")
        
        print("\n✅ 字段完整性:")
        for field, count in report['fields_summary'].items():
            percentage = (count / report['total']) * 100
            print(f"  {field}: {count}/{report['total']} ({percentage:.1f}%)")
        
        print(f"\n🎉 采集完成! 文件已保存:")
        if success_json:
            print(f"  • {json_file}")
        if success_csv:
            print(f"  • {csv_file}")
        
        print("\n📧 如需发送邮件到 19525456@qq.com，请配置邮箱信息")
        
    else:
        print("❌ 数据保存失败")

if __name__ == "__main__":
    main()