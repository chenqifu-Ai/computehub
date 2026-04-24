#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药大学获奖信息简化分析脚本
不依赖matplotlib的文本分析
"""

import json
import pandas as pd
from datetime import datetime

class TCMAwardsSimpleAnalyzer:
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
    
    def generate_comprehensive_report(self):
        """生成综合性分析报告"""
        print("生成中医药大学获奖信息综合性分析报告...")
        
        report = "# 中医药大学获奖信息综合性分析报告\n\n"
        report += f"## 📊 报告概览\n"
        report += f"- **报告时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        report += f"- **数据总量**: {len(self.data)} 条获奖记录\n"
        report += f"- **涵盖院校**: {self.df['university'].nunique()} 所重点中医药大学\n"
        report += f"- **时间范围**: {self.df['year'].min()}年 - {self.df['year'].max()}年\n"
        report += f"- **奖项种类**: {self.df['award_name'].nunique()} 种国家级和部省级奖项\n\n"
        
        # 详细统计分析
        report += self._generate_statistical_analysis()
        report += self._generate_university_analysis()
        report += self._generate_award_type_analysis()
        report += self._generate_temporal_analysis()
        report += self._generate_research_area_analysis()
        report += self._generate_excellence_analysis()
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f'tcm_awards_comprehensive_analysis_{timestamp}.md'
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"综合性分析报告已保存到: {report_filename}")
        return report_filename
    
    def _generate_statistical_analysis(self):
        """生成统计分析"""
        analysis = "## 📈 统计分析\n\n"
        
        # 大学排名
        uni_ranking = self.df['university'].value_counts()
        analysis += "### 大学获奖数量排名\n"
        for i, (uni, count) in enumerate(uni_ranking.items(), 1):
            percentage = (count / len(self.data)) * 100
            analysis += f"{i}. **{uni}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        # 奖项类型分布
        award_dist = self.df['award_name'].value_counts()
        analysis += "### 奖项类型分布\n"
        for award_type, count in award_dist.items():
            percentage = (count / len(self.data)) * 100
            analysis += f"- **{award_type}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        return analysis
    
    def _generate_university_analysis(self):
        """生成大学详细分析"""
        analysis = "## 🎓 各大学详细分析\n\n"
        
        for uni in self.df['university'].unique():
            uni_data = self.df[self.df['university'] == uni]
            analysis += f"### {uni}\n"
            analysis += f"**获奖总数**: {len(uni_data)} 项\n\n"
            
            # 奖项类型分布
            award_types = uni_data['award_name'].value_counts()
            analysis += "**奖项类型**:\n"
            for award_type, count in award_types.items():
                analysis += f"- {award_type}: {count} 项\n"
            analysis += "\n"
            
            # 获奖等级
            levels = uni_data['level'].value_counts()
            analysis += "**获奖等级**:\n"
            for level, count in levels.items():
                analysis += f"- {level}: {count} 项\n"
            analysis += "\n"
            
            # 代表项目
            analysis += "**代表项目**:\n"
            for _, row in uni_data.iterrows():
                analysis += f"- {row['year']}年 {row['level']}: {row['project']}\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_award_type_analysis(self):
        """生成奖项类型分析"""
        analysis = "## 🏆 奖项类型深度分析\n\n"
        
        for award_type in self.df['award_name'].unique():
            award_data = self.df[self.df['award_name'] == award_type]
            analysis += f"### {award_type}\n"
            analysis += f"**总数量**: {len(award_data)} 项\n"
            
            # 大学分布
            uni_dist = award_data['university'].value_counts()
            analysis += "**大学分布**:\n"
            for uni, count in uni_dist.items():
                analysis += f"- {uni}: {count} 项\n"
            analysis += "\n"
            
            # 时间分布
            year_dist = award_data['year'].value_counts().sort_index()
            analysis += "**时间分布**:\n"
            for year, count in year_dist.items():
                analysis += f"- {year}年: {count} 项\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_temporal_analysis(self):
        """生成时间趋势分析"""
        analysis = "## 📅 时间趋势分析\n\n"
        
        year_trend = self.df['year'].value_counts().sort_index()
        analysis += "### 年度获奖数量\n"
        for year, count in year_trend.items():
            analysis += f"- **{year}年**: {count} 项\n"
        analysis += "\n"
        
        # 计算年均增长
        years = sorted(self.df['year'].unique())
        if len(years) > 1:
            first_year = min(years)
            last_year = max(years)
            first_count = year_trend.get(str(first_year), 0)
            last_count = year_trend.get(str(last_year), 0)
            
            if first_count > 0:
                growth_rate = ((last_count - first_count) / first_count) * 100
                analysis += f"**增长分析**: 从{first_year}年到{last_year}年，获奖数量从{first_count}项增加到{last_count}项，增长{growth_rate:+.1f}%\n\n"
        
        return analysis
    
    def _generate_research_area_analysis(self):
        """生成研究领域分析"""
        analysis = "## 🔬 研究领域分析\n\n"
        
        category_dist = self.df['category'].value_counts()
        analysis += "### 研究领域分布\n"
        for category, count in category_dist.items():
            percentage = (count / len(self.data)) * 100
            analysis += f"- **{category}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        # 各领域代表大学
        analysis += "### 各研究领域的领先大学\n"
        for category in self.df['category'].unique():
            category_data = self.df[self.df['category'] == category]
            top_unis = category_data['university'].value_counts().head(3)
            analysis += f"**{category}**:\n"
            for uni, count in top_unis.items():
                analysis += f"- {uni}: {count} 项\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_excellence_analysis(self):
        """生成卓越成就分析"""
        analysis = "## 🌟 卓越成就亮点\n\n"
        
        # 特等奖项目
        special_awards = self.df[self.df['level'] == '特等奖']
        if not special_awards.empty:
            analysis += "### 特等奖项目\n"
            for _, row in special_awards.iterrows():
                analysis += f"- **{row['university']}** ({row['year']}年): {row['project']}\n"
                analysis += f"  详情: {row['details']}\n"
            analysis += "\n"
        
        # 一等奖项目
        first_awards = self.df[self.df['level'] == '一等奖']
        if not first_awards.empty:
            analysis += "### 一等奖代表性项目\n"
            for _, row in first_awards.head(5).iterrows():  # 显示前5个
                analysis += f"- **{row['university']}** ({row['year']}年): {row['project']}\n"
            analysis += "\n"
        
        # 近年重要成果
        recent_awards = self.df[self.df['year'].astype(int) >= 2020]
        if not recent_awards.empty:
            analysis += "### 近年重要成果 (2020年以后)\n"
            for _, row in recent_awards.iterrows():
                analysis += f"- **{row['university']}** ({row['year']}年 {row['level']}): {row['project']}\n"
            analysis += "\n"
        
        return analysis
    
    def generate_statistical_summary(self):
        """生成统计摘要"""
        summary = {
            'total_awards': len(self.data),
            'universities': list(self.df['university'].unique()),
            'universities_count': self.df['university'].nunique(),
            'award_types': list(self.df['award_name'].unique()),
            'award_types_count': self.df['award_name'].nunique(),
            'years': sorted(self.df['year'].unique()),
            'time_span': f"{self.df['year'].min()}-{self.df['year'].max()}",
            'research_areas': list(self.df['category'].unique()),
            'research_areas_count': self.df['category'].nunique(),
            'award_levels': list(self.df['level'].unique()),
            'top_university': self.df['university'].value_counts().index[0],
            'top_award_type': self.df['award_name'].value_counts().index[0],
            'most_common_level': self.df['level'].value_counts().index[0],
            'peak_year': self.df['year'].value_counts().index[0],
            'special_awards_count': len(self.df[self.df['level'] == '特等奖'])
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
    
    analyzer = TCMAwardsSimpleAnalyzer(data_file)
    
    # 生成综合性分析报告
    report_file = analyzer.generate_comprehensive_report()
    
    # 生成统计摘要
    summary, summary_file = analyzer.generate_statistical_summary()
    
    print("\n" + "=" * 70)
    print("深度分析完成!")
    print(f"分析报告: {report_file}")
    print(f"统计摘要: {summary_file}")
    print("=" * 70)
    
    # 显示关键统计信息
    print("\n📊 关键统计信息:")
    print(f"• 总获奖数: {summary['total_awards']} 项")
    print(f"• 涵盖大学: {summary['universities_count']} 所")
    print(f"• 时间跨度: {summary['time_span']} 年")
    print(f"• 奖项类型: {summary['award_types_count']} 种")
    print(f"• 研究领域: {summary['research_areas_count']} 个")
    print(f"• 获奖最多大学: {summary['top_university']}")
    print(f"• 最主要奖项: {summary['top_award_type']}")
    print(f"• 特等奖项目: {summary['special_awards_count']} 项")

if __name__ == "__main__":
    main()