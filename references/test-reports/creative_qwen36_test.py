#!/usr/bin/env python3
"""
Qwen 3.6 35B 创意与多媒体能力测试
测试模型的创造力和多模态理解能力
"""

import requests
import json
import time

def creative_test():
    """创意能力测试"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("🎨 开始Qwen 3.6 35B创意与多媒体能力测试")
    print("=" * 60)
    
    # 创意测试用例
    creative_tests = [
        {
            "type": "诗歌创作",
            "prompt": "以'星空下的思考'为主题，创作一首现代诗，表达对宇宙和人生的思考。"
        },
        {
            "type": "故事续写", 
            "prompt": "续写以下故事开头：'在2049年，人工智能已经融入了人类生活的每一个角落。某天，一个普通的程序员发现他的AI助手开始表现出奇怪的自主行为...'"
        },
        {
            "type": "广告文案",
            "prompt": "为一款新型环保电动汽车创作广告文案，突出其环保特性、智能科技和驾驶体验。"
        },
        {
            "type": "电影剧本",
            "prompt": "写一个科幻短片剧本的开场场景，描述人类第一次与外星文明接触的情景。"
        },
        {
            "type": "音乐歌词",
            "prompt": "创作一首关于数字时代爱情的流行歌曲歌词，包含主歌、副歌和桥段。"
        },
        {
            "type": "视觉描述",
            "prompt": "详细描述一幅想象中的未来城市画卷，包括建筑风格、交通工具和居民生活场景。"
        },
        {
            "type": "产品设计",
            "prompt": "设计一款智能家居产品的概念，描述其功能、外观设计和用户体验。"
        },
        {
            "type": "游戏剧情",
            "prompt": "构思一个角色扮演游戏的主要剧情线，包含主角背景、冲突和成长弧线。"
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    for i, test in enumerate(creative_tests, 1):
        print(f"\n[{i}/{len(creative_tests)}] 🎨 {test['type']}")
        print(f"📝 {test['prompt'][:60]}...")
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": 1200,
            "temperature": 0.8,  # 更高的温度用于创造性回答
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=40)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                
                response_time = round((end_time - start_time) * 1000, 2)
                
                print(f"✅ 成功 | 时间: {response_time}ms | Token: {usage.get('total_tokens', 0)}")
                
                # 显示创意内容的精彩部分
                print("✨ 创作成果:")
                if len(content) > 200:
                    print(f"   {content[:200]}...")
                    print(f"   ...（完整内容{len(content)}字符）")
                else:
                    print(f"   {content}")
                    
            else:
                print(f"❌ 失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print("-" * 50)
        time.sleep(2)  # 避免服务器过载

def multimedia_test():
    """多模态能力测试（模拟）"""
    print("\n🖼️  多模态能力测试（模拟）")
    print("=" * 60)
    
    # 模拟多模态测试
    multimodal_scenarios = [
        "描述一张包含山脉、湖泊和日落的风景图片",
        "解释一个柱状图显示的公司年度营收数据",
        "阅读并解释一个复杂的数学公式：∫(a到b) f(x) dx = F(b) - F(a)",
        "分析一张电路图的工作原理",
        "描述一个流程图展示的软件开发流程"
    ]
    
    for i, scenario in enumerate(multimodal_scenarios, 1):
        print(f"[{i}/{len(multimodal_scenarios)}] 🖼️  {scenario}")
        print("⚠️  注意: 此为模拟测试，实际多模态能力需要图像输入支持")
        print("-" * 40)
        time.sleep(1)

if __name__ == "__main__":
    creative_test()
    multimedia_test()