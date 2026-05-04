#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药大学获奖信息深度分析脚本
提供数据可视化和深入分析
"""

import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TCMAwardsAnalyzer:
    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self.load_data()
        self.df = self.create_dataframe()
    
    def load_data(self):
        """加载数据"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_dataframe(self):
        """创建数据分析用的DataFrame"""
        return pd.DataFrame(self.data)
    
    def generate_analysis_report(self):
        """生成分析报告"""
        print("开始生成中医药大学获奖信息深度分析报告...")
        
        # 创建分析报告
        report = "# 中医药大学获奖信息深度分析报告\n\n"
        report += f"## 分析时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        report += f"## 数据概况\n"
        report += f"- 总数据量: {len(self.data)} 条获奖记录\n"
        report += f"- 涵盖大学: {self.df['university'].nunique()} 所\n"
        report += f"- 时间跨度: {self.df['year'].min()}年 - {self.df['year'].max()}年\n"
        report += f"- 奖项类型: {self.df['award_name'].nunique()} 种\n\n"
        
        # 大学排名分析
        report += "## 大学获奖排名分析\n"
        uni_ranking = self.df['university'].value_counts()
        for i, (uni, count) in enumerate(uni_ranking.items(), 1):
            report += f"{i}. {uni}: {count} 项\n"
        report += "\n"
        
        # 奖项类型分析
        report += "## 奖项类型分析\n"
        award_type_analysis = self.df['award_name'].value_counts()
        for award_type, count in award_type_analysis.items():
            percentage = (count / len(self.data)) * 100
            report += f"- {award_type}: {count} 项 ({percentage:.1f}%)\n"
        report += "\n"
        
        # 获奖等级分析
        report += "## 获奖等级分析\n"
        level_analysis = self.df['level'].value_counts()
        for level, count in level_analysis.items():
            percentage = (count / len(self.data)) * 100
            report += f"- {level}: {count} 项 ({percentage:.1f}%)\n"
        report += "\n"
        
        # 时间趋势分析
        report += "## 时间趋势分析\n"
        year_trend = self.df['year'].value_counts().sort_index()
        for year, count in year_trend.items():
            report += f"- {year}年: {count} 项\n"
        report += "\n"
        
        # 研究领域分析
        report += "## 研究领域分布\n"
        category_analysis = self.df['category'].value_counts()
        for category, count in category_analysis.items():
            percentage = (count / len(self.data)) * 100
            report += f"- {category}: {count} 项 ({percentage:.1f}%)\n"
        report += "\n"
        
        # 各大学优势领域
        report += "## 各大学优势研究领域\n"
        for uni in self.df['university'].unique():
            uni_data = self.df[self.df['university'] == uni]
            top_categories = uni_data['category'].value_counts().head(3)
            report += f"### {uni}\n"
            for category, count in top_categories.items():
                report += f"- {category}: {count} 项\n"
            report += "\n"
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f'tcm_awards_analysis_report_{timestamp}.md'
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"分析报告已保存到: {report_filename}")
        return report_filename
    
    def create_visualizations(self):
        """创建数据可视化图表"""
        print("创建数据可视化图表...")
        
        # 创建图表目录
        import os
        viz_dir = "tcm_awards_visualizations"
        os.makedirs(viz_dir, exist_ok=True)
        
        # 1. 大学获奖数量柱状图
        plt.figure(figsize=(12, 8))
        uni_counts = self.df['university'].value_counts()
        uni_counts.plot(kind='bar', color='skyblue')
        plt.title('各中医药大学获奖数量对比', fontsize=16, fontweight='bold')
        plt.xlabel('大学名称', fontsize=12)
        plt.ylabel('获奖数量', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/university_awards_count.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. 奖项类型分布饼图
        plt.figure(figsize=(10, 8))
        award_counts = self.df['award_name'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(award_counts)))
        wedges, texts, autotexts = plt.pie(award_counts.values, labels=award_counts.index, 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        plt.title('奖项类型分布', fontsize=16, fontweight='bold')
        plt.savefig(f'{viz_dir}/award_type_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. 时间趋势折线图
        plt.figure(figsize=(12, 6))
        year_trend = self.df['year'].value_counts().sort_index()
        plt.plot(year_trend.index.astype(str), year_trend.values, marker='o', linewidth=2, markersize=8)
        plt.title('获奖数量年度趋势', fontsize=16, fontweight='bold')
        plt.xlabel('年份', fontsize=12)
        plt.ylabel('获奖数量', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/yearly_trend.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. 获奖等级分布
        plt.figure(figsize=(10, 6))
        level_counts = self.df['level'].value_counts()
        level_colors = ['gold', 'silver', 'peru']  # 金、银、铜色
        level_counts.plot(kind='bar', color=level_colors[:len(level_counts)])
        plt.title('获奖等级分布', fontsize=16, fontweight='bold')
        plt.xlabel('获奖等级', fontsize=12)
        plt.ylabel('数量', fontsize=12)
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/award_level_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 5. 研究领域热力图
        plt.figure(figsize=(14, 8))
        category_uni_cross = pd.crosstab(self.df['category'], self.df['university'])
        sns.heatmap(category_uni_cross, annot=True, cmap='YlOrRd', fmt='d')
        plt.title('各大学研究领域分布热力图', fontsize=16, fontweight='bold')
        plt.xlabel('大学', fontsize=12)
        plt.ylabel('研究领域', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/research_area_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"可视化图表已保存到 {viz_dir}/ 目录")
        return viz_dir
    
    def generate_statistical_summary(self):
        """生成统计摘要"""
        print("生成统计摘要...")
        
        summary = {
            'total_awards': len(self.data),
            'universities_count': self.df['university'].nunique(),
            'award_types_count': self.df['award_name'].nunique(),
            'years_covered': f"{self.df['year'].min()}-{self.df['year'].max()}",
            'top_university': self.df['university'].value_counts().index[0],
            'top_award_type': self.df['award_name'].value_counts().index[0],
            'most_common_level': self.df['level'].value_counts().index[0],
            'peak_year': self.df['year'].value_counts().index[0]
        }
        
        # 保存统计摘要
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f'tcm_awards_statistical_summary_{timestamp}.json'
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"统计摘要已保存到: {summary_filename}")
        return summary, summary_filename

def main():
    """主函数"""
    data_file = 'tcm_awards_complete_data_20260414_041229.json'
    
    print("=" * 70)
    print("中医药大学获奖信息深度分析系统")
    print("=" * 70)
    
    analyzer = TCMAwardsAnalyzer(data_file)
    
    # 生成分析报告
    report_file = analyzer.generate_analysis_report()
    
    # 创建可视化图表
    viz_dir = analyzer.create_visualizations()
    
    # 生成统计摘要
    summary, summary_file = analyzer.generate_statistical_summary()
    
    print("\n" + "=" * 70)
    print("深度分析完成!")
    print(f"分析报告: {report_file}")
    print(f"可视化图表: {viz_dir}/")
    print(f"统计摘要: {summary_file}")
    print("=" * 70)
    
    # 显示关键统计信息
    print("\n📊 关键统计信息:")
    print(f"• 总获奖数: {summary['total_awards']} 项")
    print(f"• 涵盖大学: {summary['universities_count']} 所")
    print(f"• 时间跨度: {summary['years_covered']} 年")
    print(f"• 获奖最多大学: {summary['top_university']}")
    print(f"• 最主要奖项: {summary['top_award_type']}")
    print(f"• 最常获奖等级: {summary['most_common_level']}")
    print(f"• 获奖高峰年: {summary['peak_year']}年")

if __name__ == "__main__":
    main()