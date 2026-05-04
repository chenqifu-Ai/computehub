#!/usr/bin/env python3
"""
PDF生成脚本 - 使用reportlab库生成精美的PDF规格书
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
import os

def create_pdf_specification():
    """创建精美的PDF规格书"""
    
    # 创建PDF文档
    pdf_path = "/root/.openclaw/workspace/zhiqitong_specification.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    
    # 获取样式
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1  # 居中
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', 
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=20
    )
    
    # 构建内容
    story = []
    
    # 标题
    story.append(Paragraph("🚀 智企通AI解决方案", title_style))
    story.append(Paragraph("让每家企业都用得起、用得好AI智能化管理", styles['Heading3']))
    story.append(Spacer(1, 20))
    
    # 产品概述
    story.append(Paragraph("📦 产品体系概览", subtitle_style))
    
    # 价格表格
    pricing_data = [
        ['版本', '适合规模', '价格', '核心价值'],
        ['🎪 启航版', '5-10人团队', '¥9,800', '数字化入门，基础AI办公'],
        ['⚡ 成长版', '10-20人团队', '¥16,800', '全面数字化，智能管理'],
        ['🚀 卓越版', '20-50人团队', '¥26,800', '专业级AI，行业定制']
    ]
    
    pricing_table = Table(pricing_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 3*inch])
    pricing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    
    story.append(pricing_table)
    story.append(Spacer(1, 30))
    
    # 硬件配置
    story.append(Paragraph("🖥️ 硬件配置精华", subtitle_style))
    
    hardware_data = [
        ['配置项', '启航版', '成长版', '卓越版'],
        ['CPU', 'Intel i5-13500', 'Intel i7-13700', 'Intel i9-13900'],
        ['内存', '32GB DDR4', '64GB DDR5', '128GB DDR5'],
        ['存储', '1TB NVMe SSD', '2TB NVMe + 4TB HDD', '4TB NVMe + 8TB HDD RAID1'],
        ['显卡', '集成显卡', 'RTX 4060 8GB', 'RTX 4070 Ti 12GB'],
        ['网络', '2.5G双网口', '2.5G + Wi-Fi 6E', '10G光纤 + 2.5G铜缆']
    ]
    
    hardware_table = Table(hardware_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    hardware_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    
    story.append(hardware_table)
    story.append(Spacer(1, 30))
    
    # AI能力
    story.append(Paragraph("🤖 AI核心能力", subtitle_style))
    
    ai_data = [
        ['AI类型', '模型', '能力描述'],
        ['📝 文本AI', 'DeepSeek-Coder', '专业代码生成和调试'],
        ['📝 文本AI', 'Llama3', '通用对话和文档写作'],
        ['👁️ 视觉AI', 'YOLOv8', '实时物体检测识别'],
        ['🎤 语音AI', 'Whisper', '高精度语音识别转录']
    ]
    
    ai_table = Table(ai_data, colWidths=[1.5*inch, 2*inch, 3.5*inch])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    
    story.append(ai_table)
    story.append(Spacer(1, 30))
    
    # 性能指标
    story.append(Paragraph("📊 性能指标", subtitle_style))
    
    performance_data = [
        ['指标', '标准', '实际表现'],
        ['响应时间', '< 2秒', '0.8-1.5秒'],
        ['并发处理', '10会话', '12-15会话'],
        ['准确率', '>85%', '88-92%'],
        ['系统可用性', '99.9%', '99.95%']
    ]
    
    performance_table = Table(performance_data, colWidths=[2*inch, 2*inch, 2*inch])
    performance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    
    story.append(performance_table)
    story.append(Spacer(1, 30))
    
    # 投资回报
    story.append(Paragraph("💰 投资回报分析", subtitle_style))
    
    roi_text = """
    💵 <b>成本对比:</b>
    • SAAS服务: ¥500-5000/月 × 12 = ¥6000-60000/年
    • 智企通: ¥9800-26800 → 用5年 → 年均¥1960-5360
    • <font color='#ff6b6b'>节省比例: 67-91% 成本节省！</font>
    
    📈 <b>回报分析:</b>
    • 投资回收期: 3-10个月
    • 年化ROI: 300-800%  
    • 人力节省: 2-5人/年
    • 效率提升: 30-50%
    """
    
    story.append(Paragraph(roi_text, styles['Normal']))
    story.append(Spacer(1, 30))
    
    # 联系信息
    story.append(Paragraph("📞 联系我们", subtitle_style))
    
    contact_text = """
    🎯 <b>立即体验智企通</b>
    
    📞 <b>服务热线</b>: 400-888-智企  
    🌐 <b>官方网站</b>: www.zhiqi.ai  
    📧 <b>商务合作</b>: business@zhiqi.ai  
    🔧 <b>技术支持</b>: support@zqi.ai
    
    📍 <b>公司地址</b>: 上海市浦东新区张江高科技园区
    """
    
    story.append(Paragraph(contact_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # 页脚
    footer_text = """
    <i>智企科技 - 让AI赋能每一家企业</i>
    <br/>
    <font size="9">最后更新: 2026-04-16 | 版本: v1.0 | 保密等级: 内部公开</font>
    """
    
    story.append(Paragraph(footer_text, styles['Italic']))
    
    # 生成PDF
    try:
        doc.build(story)
        print(f"✅ PDF生成成功: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ PDF生成失败: {e}")
        return None

if __name__ == "__main__":
    # 检查reportlab是否可用
    try:
        import reportlab
        pdf_path = create_pdf_specification()
        if pdf_path:
            print("🎉 精美PDF规格书已生成！")
        else:
            print("❌ PDF生成失败")
    except ImportError:
        print("❌ reportlab库未安装，无法生成PDF")
        print("💡 请安装: pip install reportlab")
        
        # 提供替代方案
        print("\n📋 替代方案:")
        print("1. 使用浏览器打开HTML文件后打印为PDF")
        print("2. 使用在线HTML转PDF工具")
        print("3. 安装reportlab: pip install reportlab")
        
        # 检查当前环境
        print("\n🔧 当前环境:")
        import subprocess
        result = subprocess.run(["pip", "list"], capture_output=True, text=True)
        if "reportlab" in result.stdout:
            print("✅ reportlab已安装")
        else:
            print("❌ reportlab未安装")
            
            # 尝试安装
            print("\n🔄 尝试安装reportlab...")
            try:
                subprocess.run(["pip", "install", "reportlab"], check=True)
                print("✅ reportlab安装成功")
                pdf_path = create_pdf_specification()
            except:
                print("❌ reportlab安装失败")