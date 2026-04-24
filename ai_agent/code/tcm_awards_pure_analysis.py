#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药大学获奖信息纯Python分析脚本
不依赖任何外部库
"""

import json
from datetime import datetime
from collections import Counter, defaultdict

class TCMAwardsPureAnalyzer:
    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self.load_data()
    
    def load_data(self):
        """加载数据"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_comprehensive_report(self):
        """生成综合性分析报告"""
        print("生成中医药大学获奖信息综合性分析报告...")
        
        # 基础统计
        total_awards = len(self.data)
        universities = set(item['university'] for item in self.data)
        years = sorted(set(item['year'] for item in self.data))
        award_types = set(item['award_name'] for item in self.data)
        
        report = "# 中医药大学获奖信息综合性分析报告\n\n"
        report += f"## 📊 报告概览\n"
        report += f"- **报告时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        report += f"- **数据总量**: {total_awards} 条获奖记录\n"
        report += f"- **涵盖院校**: {len(universities)} 所重点中医药大学\n"
        report += f"- **时间范围**: {min(years)}年 - {max(years)}年\n"
        report += f"- **奖项种类**: {len(award_types)} 种国家级和部省级奖项\n\n"
        
        # 详细统计分析
        report += self._generate_statistical_analysis()
        report += self._generate_university_analysis()
        report += self._generate_award_type_analysis()
        report += self._generate_temporal_analysis()
        report += self._generate_research_area_analysis()
        report += self._generate_excellence_analysis()
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f'tcm_awards_pure_analysis_{timestamp}.md'
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"综合性分析报告已保存到: {report_filename}")
        return report_filename
    
    def _generate_statistical_analysis(self):
        """生成统计分析"""
        analysis = "## 📈 统计分析\n\n"
        
        # 大学排名
        uni_counter = Counter(item['university'] for item in self.data)
        analysis += "### 大学获奖数量排名\n"
        for i, (uni, count) in enumerate(uni_counter.most_common(), 1):
            percentage = (count / len(self.data)) * 100
            analysis += f"{i}. **{uni}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        # 奖项类型分布
        award_counter = Counter(item['award_name'] for item in self.data)
        analysis += "### 奖项类型分布\n"
        for award_type, count in award_counter.most_common():
            percentage = (count / len(self.data)) * 100
            analysis += f"- **{award_type}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        return analysis
    
    def _generate_university_analysis(self):
        """生成大学详细分析"""
        analysis = "## 🎓 各大学详细分析\n\n"
        
        # 按大学分组数据
        uni_data = defaultdict(list)
        for item in self.data:
            uni_data[item['university']].append(item)
        
        for uni, items in sorted(uni_data.items(), key=lambda x: len(x[1]), reverse=True):
            analysis += f"### {uni}\n"
            analysis += f"**获奖总数**: {len(items)} 项\n\n"
            
            # 奖项类型分布
            award_types = Counter(item['award_name'] for item in items)
            analysis += "**奖项类型**:\n"
            for award_type, count in award_types.most_common():
                analysis += f"- {award_type}: {count} 项\n"
            analysis += "\n"
            
            # 获奖等级
            levels = Counter(item['level'] for item in items)
            analysis += "**获奖等级**:\n"
            for level, count in levels.most_common():
                analysis += f"- {level}: {count} 项\n"
            analysis += "\n"
            
            # 代表项目
            analysis += "**代表项目**:\n"
            for item in sorted(items, key=lambda x: x['year'], reverse=True)[:5]:  # 显示最近5个
                analysis += f"- {item['year']}年 {item['level']}: {item['project']}\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_award_type_analysis(self):
        """生成奖项类型分析"""
        analysis = "## 🏆 奖项类型深度分析\n\n"
        
        # 按奖项类型分组
        award_data = defaultdict(list)
        for item in self.data:
            award_data[item['award_name']].append(item)
        
        for award_type, items in award_data.items():
            analysis += f"### {award_type}\n"
            analysis += f"**总数量**: {len(items)} 项\n"
            
            # 大学分布
            uni_dist = Counter(item['university'] for item in items)
            analysis += "**大学分布**:\n"
            for uni, count in uni_dist.most_common():
                analysis += f"- {uni}: {count} 项\n"
            analysis += "\n"
            
            # 时间分布
            year_dist = Counter(item['year'] for item in items)
            analysis += "**时间分布**:\n"
            for year, count in sorted(year_dist.items()):
                analysis += f"- {year}年: {count} 项\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_temporal_analysis(self):
        """生成时间趋势分析"""
        analysis = "## 📅 时间趋势分析\n\n"
        
        year_counter = Counter(item['year'] for item in self.data)
        analysis += "### 年度获奖数量\n"
        for year, count in sorted(year_counter.items()):
            analysis += f"- **{year}年**: {count} 项\n"
        analysis += "\n"
        
        # 计算增长趋势
        years = sorted(year_counter.keys())
        if len(years) > 1:
            first_year = min(years)
            last_year = max(years)
            first_count = year_counter[first_year]
            last_count = year_counter[last_year]
            
            if first_count > 0:
                growth_rate = ((last_count - first_count) / first_count) * 100
                analysis += f"**增长分析**: 从{first_year}年到{last_year}年，获奖数量从{first_count}项增加到{last_count}项，增长{growth_rate:+.1f}%\n\n"
        
        return analysis
    
    def _generate_research_area_analysis(self):
        """生成研究领域分析"""
        analysis = "## 🔬 研究领域分析\n\n"
        
        category_counter = Counter(item['category'] for item in self.data)
        analysis += "### 研究领域分布\n"
        for category, count in category_counter.most_common():
            percentage = (count / len(self.data)) * 100
            analysis += f"- **{category}**: {count} 项 ({percentage:.1f}%)\n"
        analysis += "\n"
        
        # 各领域代表大学
        category_data = defaultdict(list)
        for item in self.data:
            category_data[item['category']].append(item)
        
        analysis += "### 各研究领域的领先大学\n"
        for category, items in category_data.items():
            uni_counter = Counter(item['university'] for item in items)
            analysis += f"**{category}**:\n"
            for uni, count in uni_counter.most_common(3):  # 显示前三名
                analysis += f"- {uni}: {count} 项\n"
            analysis += "\n"
        
        return analysis
    
    def _generate_excellence_analysis(self):
        """生成卓越成就分析"""
        analysis = "## 🌟 卓越成就亮点\n\n"
        
        # 特等奖项目
        special_awards = [item for item in self.data if item['level'] == '特等奖']
        if special_awards:
            analysis += "### 特等奖项目\n"
            for item in special_awards:
                analysis += f"- **{item['university']}** ({item['year']}年): {item['project']}\n"
                analysis += f"  详情: {item['details']}\n"
            analysis += "\n"
        
        # 一等奖项目
        first_awards = [item for item in self.data if item['level'] == '一等奖']
        if first_awards:
            analysis += "### 一等奖代表性项目\n"
            for item in sorted(first_awards, key=lambda x: x['year'], reverse=True)[:5]:  # 最近5个
                analysis += f"- **{item['university']}** ({item['year']}年): {item['project']}\n"
            analysis += "\n"
        
        # 近年重要成果
        recent_awards = [item for item in self.data if int(item['year']) >= 2020]
        if recent_awards:
            analysis += "### 近年重要成果 (2020年以后)\n"
            for item in sorted(recent_awards, key=lambda x: x['year'], reverse=True):
                analysis += f"- **{item['university']}** ({item['year']}年 {item['level']}): {item['project']}\n"
            analysis += "\n"
        
        return analysis
    
    def generate_statistical_summary(self):
        """生成统计摘要"""
        summary = {
            'total_awards': len(self.data),
            'universities': sorted(set(item['university'] for item in self.data)),
            'universities_count': len(set(item['university'] for item in self.data)),
            'award_types': sorted(set(item['award_name'] for item in self.data)),
            'award_types_count': len(set(item['award_name'] for item in self.data)),
            'years': sorted(set(item['year'] for item in self.data)),
            'time_span': f"{min(item['year'] for item in self.data)}-{max(item['year'] for item in self.data)}",
            'research_areas': sorted(set(item['category'] for item in self.data)),
            'research_areas_count': len(set(item['category'] for item in self.data)),
            'award_levels': sorted(set(item['level'] for item in self.data)),
            'top_university': Counter(item['university'] for item in self.data).most_common(1)[0][0],
            'top_award_type': Counter(item['award_name'] for item in self.data).most_common(1)[0][0],
            'most_common_level': Counter(item['level'] for item in self.data).most_common(1)[0][0],
            'peak_year': Counter(item['year'] for item in self.data).most_common(1)[0][0],
            'special_awards_count': len([item for item in self.data if item['level'] == '特等奖'])
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
    
    analyzer = TCMAwardsPureAnalyzer(data_file)
    
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