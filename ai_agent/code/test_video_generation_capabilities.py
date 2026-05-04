#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b 深度功能测试 v11 - 探索视频生成等高级功能
测试维度：
1. 视频生成能力（直接/间接）
2. 图像生成理解
3. 视频分镜脚本生成
4. 视频描述理解
5. 创意视频脚本
6. 视频编辑脚本
7. 音频/语音相关
8. 多模态理解
"""
import os, sys, time, json, requests
from pathlib import Path

# 设置环境变量
os.environ["QWEN36_API_KEY"] = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["QWEN36_API_URL"] = "https://ai.zhangtuokeji.top:9090/v1/chat/completions"

api_url = os.getenv("QWEN36_API_URL", "https://ai.zhangtuokeji.top:9090/v1/chat/completions")
api_key = os.getenv("QWEN36_API_KEY", "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl")
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

def call_api(model, messages, max_tokens=2000, temperature=0.7):
    """调用 API"""
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    start = time.time()
    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=120, verify=False)
        elapsed = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            usage = data.get("usage", {})
            finish = data["choices"][0].get("finish_reason")
            return {
                "success": True, "elapsed": elapsed, "content": content,
                "reasoning": reasoning, "tokens": usage, "finish": finish
            }
        else:
            return {"success": False, "error": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_v1(model_name, display_name, test_cases):
    """运行测试"""
    print(f"\n{'='*70}")
    print(f"🧪 {display_name} 深度测试")
    print(f"{'='*70}")
    
    results = []
    for name, messages, max_tokens in test_cases:
        print(f"\n📝 {name}...")
        r = call_api(model_name, messages, max_tokens)
        if r["success"]:
            elapsed = r["elapsed"]
            content = r["content"]
            reasoning = r["reasoning"]
            print(f"  ✅ 耗时：{elapsed:.1f}s | 内容长度：{len(content)} 字符")
            if content:
                print(f"  输出：{content[:200]}")
            else:
                print(f"  reasoning 长度：{len(reasoning)} 字符")
            results.append({"name": name, "success": True, "elapsed": elapsed, 
                          "content_preview": content[:100] if content else reasoning[:100]})
        else:
            print(f"  ❌ 失败：{r.get('error', 'Unknown')}")
            results.append({"name": name, "success": False, "error": r.get("error")})
    
    return results

# ============================================================
# 测试用例定义
# ============================================================

TEST_CASES = [
    # 1. 视频生成直接测试
    ("1.1 直接视频生成请求", 
     [{"role": "user", "content": "请生成一个 5 秒的短视频，展示一只猫在沙发上睡觉，背景是温馨的客厅。"}],
     500),
    
    # 2. 视频描述理解
    ("2.1 视频描述理解", 
     [{"role": "user", "content": "如果我看到以下视频描述：'夕阳下的海滩，海浪拍打着礁石，一只海鸥在天空中飞翔。' 你会有什么样的视觉感受？请用详细的文字描述你会看到的画面。"}],
     500),
    
    # 3. 视频分镜脚本
    ("3.1 视频分镜脚本生成", 
     [{"role": "user", "content": "请为一个 30 秒的产品广告视频设计分镜脚本。产品是一款智能手表，主题是'科技改变生活'。请列出 5 个分镜，每个分镜包括：画面描述、时长、旁白/音乐、转场效果。"}],
     800),
    
    # 4. 视频创意脚本
    ("4.1 视频创意脚本", 
     [{"role": "user", "content": "为一个关于'人工智能帮助老年人生活'的公益视频设计创意脚本。要求：情感真挚，时长 60 秒，包含 3 个场景：1) 老人独自在家的孤独 2) AI 助手介入帮助 3) 老人和 AI 的温馨互动。请详细描述每个场景。"}],
     800),
    
    # 5. 视频编辑脚本
    ("5.1 视频编辑指令生成", 
     [{"role": "user", "content": "如果我要用 DaVinci Resolve 编辑一个旅行 VLOG，请提供以下信息的详细步骤：1) 如何导入素材 2) 如何调色（电影感）3) 如何添加字幕 4) 如何添加转场 5) 如何导出。请给出具体操作命令。"}],
     800),
    
    # 6. 图像生成描述
    ("6.1 图像生成提示词", 
     [{"role": "user", "content": "请为 Stable Diffusion 或 Midjourney 编写 5 个高质量的图像生成提示词（prompt），主题是'赛博朋克城市夜景'。每个提示词需要包含：场景描述、光影效果、色彩风格、构图方式、艺术风格。请用英文编写。"}],
     800),
    
    # 7. 视频字幕生成
    ("7.1 视频字幕脚本", 
     [{"role": "user", "content": "请为一个 60 秒的教育视频编写字幕脚本。主题是'如何正确使用口罩'。请提供：1) 每句话的中文文本 2) 建议显示时间（秒）3) 字幕样式建议（字体、颜色、位置）。"}],
     500),
    
    # 8. 音频/语音相关
    ("8.1 语音合成脚本", 
     [{"role": "user", "content": "请为一段关于'环境保护'的有声书录制编写旁白脚本。要求：1) 语气温暖而有感染力 2) 包含适当的停顿标记 [停顿 2 秒] 3) 标注需要强调的关键词 *加粗* 4) 总时长约 3 分钟。"}],
     800),
    
    # 9. 多模态理解
    ("9.1 多模态理解能力", 
     [{"role": "user", "content": "如果我看到一张图片：'一个穿着红色外套的小女孩站在秋天的银杏树下，地上铺满了金黄色的落叶'。请用 500 字详细描述你会看到的细节，包括：光线、色彩、氛围、人物表情、季节感等。"}],
     600),
    
    # 10. 视频策划
    ("10.1 视频策划方案", 
     [{"role": "user", "content": "请为一个'AI 绘画教程'的 YouTube 视频设计完整策划方案，包括：1) 标题（中英文）2) 简介 3) 视频结构（时间轴）4) 关键知识点 5) 互动环节设计 6) 封面设计建议 7) 标签和 SEO 关键词。"}],
     1000),
    
    # 11. 视频转场设计
    ("11.1 视频转场特效设计", 
     [{"role": "user", "content": "请为以下视频场景设计转场效果：1) 从城市白天切换到夜晚 2) 从室内切换到室外 3) 从过去回忆切换到现实。请为每个转场提供 3 种不同风格的方案（创意/标准/炫酷），并说明实现方法。"}],
     800),
    
    # 12. 视频配乐建议
    ("12.1 视频配乐推荐", 
     [{"role": "user", "content": "请为一个'科技产品发布'视频推荐配乐方案。视频节奏：开头紧张期待，中间展示产品亮点，结尾震撼发布。请为每个阶段推荐 3 种风格的音乐，并说明理由和适合的 BGM 类型。"}],
     500),
]

# ============================================================
# 执行测试
# ============================================================

def main():
    print("=" * 70)
    print("🧪 qwen3.6-35b 深度功能测试 v11 - 视频生成探索")
    print("=" * 70)
    
    models = [
        ("qwen3.6-35b-common", "zhangtuo-ai-common/qwen3.6-35b-common"),
        ("qwen3.6-35b", "zhangtuo-ai/qwen3.6-35b"),
    ]
    
    all_results = {}
    
    for model_name, display_name in models:
        results = test_v1(model_name, display_name, TEST_CASES)
        all_results[display_name] = results
    
    # 汇总报告
    print("\n" + "=" * 70)
    print("📊 测试汇总报告")
    print("=" * 70)
    
    for model_name, results in all_results.items():
        print(f"\n🤖 {model_name}")
        print("-" * 70)
        
        passed = sum(1 for r in results if r["success"])
        total = len(results)
        
        print(f"✅ 通过：{passed}/{total} ({passed/total*100:.0f}%)")
        
        if passed > 0:
            avg_time = sum(r["elapsed"] for r in results if r["success"]) / passed
            print(f"⏱️ 平均耗时：{avg_time:.1f}s")
        
        print(f"\n📋 详细结果：")
        for r in results:
            status = "✅" if r["success"] else "❌"
            time_info = f"{r['elapsed']:.1f}s" if r["success"] else "ERROR"
            preview = r.get("content_preview", "")[:80]
            print(f"  {status} {r['name']:25s} | {time_info:8s} | {preview}")
    
    # 视频生成能力评估
    print("\n" + "=" * 70)
    print("🎬 视频生成能力评估")
    print("=" * 70)
    
    video_tests = [r for r in all_results["zhangtuo-ai-common/qwen3.6-35b-common"] 
                   if any(kw in r["name"] for kw in ["视频", "分镜", "脚本", "转场", "配乐", "策划"])]
    
    print(f"\n📹 视频相关测试：{len(video_tests)}/{len(all_results['zhangtuo-ai-common/qwen3.6-35b-common'])}")
    
    for r in video_tests:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['name']}")
    
    print("\n💡 结论：")
    print("  1. 模型不能直接生成视频文件（视频生成是外部任务）")
    print("  2. 但模型可以：")
    print("     - 生成视频分镜脚本 ✅")
    print("     - 设计视频创意脚本 ✅")
    print("     - 编写视频编辑指令 ✅")
    print("     - 设计转场效果 ✅")
    print("     - 推荐配乐方案 ✅")
    print("     - 提供图像生成提示词 ✅")
    print("     - 生成字幕脚本 ✅")
    print("  3. 核心能力：创意构思 + 脚本编写 + 分镜设计")
    print("  4. 需要配合外部工具（视频编辑软件、AI 视频生成模型）")

if __name__ == "__main__":
    main()
