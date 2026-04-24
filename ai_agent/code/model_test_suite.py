#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量模型测试套件 - 测试所有可用模型并生成详细报告
"""

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# 测试配置
TEST_PROMPTS = [
    "你好，请简单介绍一下你自己。",
    "请计算: 123 + 456 = ?",
    "请用一句话描述人工智能的未来。"
]

TEST_MODELS = [
    "glm-4.7-flash:latest",
    "qwen:0.5b", 
    "Llama3.1:latest",
    "ministral-3:8b",
    "gemma3:4b",
    "deepseek-coder:6.7b"
]

# 结果存储
results = {
    "test_time": datetime.now().isoformat(),
    "test_environment": {
        "server": "http://192.168.1.7:11434",
        "total_models": len(TEST_MODELS),
        "test_prompts": len(TEST_PROMPTS)
    },
    "model_results": []
}

def test_model(model_name):
    """测试单个模型"""
    model_result = {
        "model_name": model_name,
        "test_status": "未知",
        "response_times": [],
        "avg_response_time": 0,
        "success_rate": 0,
        "responses": [],
        "errors": []
    }
    
    print(f"\n🧪 测试模型: {model_name}")
    print("=" * 50)
    
    success_count = 0
    total_time = 0
    
    for i, prompt in enumerate(TEST_PROMPTS):
        print(f"\n📝 测试 {i+1}/{len(TEST_PROMPTS)}: {prompt[:30]}...")
        
        try:
            start_time = time.time()
            
            # 调用模型API
            result = subprocess.run([
                "curl", "-s", "-X", "POST",
                "http://192.168.1.7:11434/api/generate",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                })
            ], capture_output=True, text=True, timeout=60)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                response_text = response_data.get("response", "")
                
                model_result["responses"].append({
                    "prompt": prompt,
                    "response": response_text[:100] + "..." if len(response_text) > 100 else response_text,
                    "response_time": response_time,
                    "status": "成功"
                })
                
                model_result["response_times"].append(response_time)
                total_time += response_time
                success_count += 1
                
                print(f"✅ 成功 - 响应时间: {response_time:.2f}秒")
                print(f"📄 响应: {response_text[:50]}...")
                
            else:
                model_result["errors"].append(f"测试{i+1}失败: {result.stderr}")
                print(f"❌ 失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            model_result["errors"].append(f"测试{i+1}超时")
            print(f"⏰ 超时 - 测试{i+1}超过60秒")
            
        except Exception as e:
            model_result["errors"].append(f"测试{i+1}异常: {str(e)}")
            print(f"❌ 异常: {str(e)}")
    
    # 计算统计指标
    if len(TEST_PROMPTS) > 0:
        model_result["success_rate"] = (success_count / len(TEST_PROMPTS)) * 100
        
    if model_result["response_times"]:
        model_result["avg_response_time"] = sum(model_result["response_times"]) / len(model_result["response_times"])
    
    # 设置测试状态
    if model_result["success_rate"] == 100:
        model_result["test_status"] = "优秀"
    elif model_result["success_rate"] >= 66:
        model_result["test_status"] = "良好"
    elif model_result["success_rate"] > 0:
        model_result["test_status"] = "部分可用"
    else:
        model_result["test_status"] = "不可用"
    
    return model_result

def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("📊 模型测试报告")
    print("=" * 60)
    
    report_lines = [
        f"# 🤖 模型测试报告",
        f"",
        f"**测试时间**: {results['test_time']}",
        f"**测试环境**: {results['test_environment']['server']}",
        f"**测试模型数**: {results['test_environment']['total_models']}",
        f"**测试提示词数**: {results['test_environment']['test_prompts']}",
        f"",
        f"## 📈 测试结果总览",
        f"",
        f"| 模型名称 | 状态 | 成功率 | 平均响应时间 | 测试结果 |",
        f"|---------|------|--------|-------------|---------|"
    ]
    
    # 生成表格
    for model in results["model_results"]:
        status_emoji = {
            "优秀": "✅",
            "良好": "🟢", 
            "部分可用": "🟡",
            "不可用": "❌"
        }.get(model["test_status"], "❓")
        
        report_lines.append(
            f"| {model['model_name']} | {status_emoji} {model['test_status']} | "
            f"{model['success_rate']:.1f}% | {model['avg_response_time']:.2f}s | "
            f"{len(model['errors'])} 错误 |"
        )
    
    # 详细结果
    report_lines.extend([
        f"",
        f"## 📋 详细测试结果",
        f""
    ])
    
    for model in results["model_results"]:
        report_lines.extend([
            f"### 🤖 {model['model_name']}",
            f"",
            f"**测试状态**: {model['test_status']}",
            f"**成功率**: {model['success_rate']:.1f}%",
            f"**平均响应时间**: {model['avg_response_time']:.2f}秒",
            f""
        ])
        
        if model["responses"]:
            report_lines.append("**成功响应示例**:")
            report_lines.append("```")
            for resp in model["responses"][:2]:  # 只显示前2个
                report_lines.append(f"问: {resp['prompt']}")
                report_lines.append(f"答: {resp['response']}")
                report_lines.append(f"时间: {resp['response_time']:.2f}s")
                report_lines.append("")
            report_lines.append("```")
        
        if model["errors"]:
            report_lines.append("**错误信息**:")
            report_lines.append("```")
            for error in model["errors"]:
                report_lines.append(f"- {error}")
            report_lines.append("```")
        
        report_lines.append("")
    
    # 性能排名
    working_models = [m for m in results["model_results"] if m["success_rate"] > 0]
    if working_models:
        working_models.sort(key=lambda x: x["avg_response_time"])
        
        report_lines.extend([
            f"## 🏆 性能排名 (按响应时间)",
            f""
        ])
        
        for i, model in enumerate(working_models, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            report_lines.append(
                f"{medal} **{model['model_name']}** - {model['avg_response_time']:.2f}秒 "
                f"(成功率: {model['success_rate']:.1f}%)"
            )
    
    # 建议
    report_lines.extend([
        f"",
        f"## 💡 使用建议",
        f""
    ])
    
    excellent_models = [m for m in results["model_results"] if m["test_status"] == "优秀"]
    if excellent_models:
        fastest = min(excellent_models, key=lambda x: x["avg_response_time"])
        report_lines.append(f"⚡ **推荐模型**: {fastest['model_name']} (最快响应)")
    
    report_lines.extend([
        f"🔧 **优化建议**: 定期测试模型性能，监控响应时间变化",
        f"📊 **监控频率**: 建议每周测试一次，确保模型稳定可用"
    ])
    
    return "\n".join(report_lines)

def main():
    """主测试流程"""
    print("🚀 开始全量模型测试...")
    print(f"测试时间: {results['test_time']}")
    print(f"测试模型数: {len(TEST_MODELS)}")
    print(f"测试提示词数: {len(TEST_PROMPTS)}")
    
    # 测试所有模型
    for model_name in TEST_MODELS:
        try:
            model_result = test_model(model_name)
            results["model_results"].append(model_result)
        except Exception as e:
            print(f"❌ 测试模型 {model_name} 失败: {str(e)}")
            results["model_results"].append({
                "model_name": model_name,
                "test_status": "测试失败",
                "success_rate": 0,
                "avg_response_time": 0,
                "errors": [str(e)]
            })
    
    # 生成报告
    report = generate_report()
    
    # 保存报告
    report_file = f"/root/.openclaw/workspace/ai_agent/results/model_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    Path(report_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存JSON结果
    json_file = report_file.replace('.md', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试完成！")
    print(f"📄 报告已保存: {report_file}")
    print(f"📊 数据已保存: {json_file}")
    
    # 输出报告
    print("\n" + report)
    
    return results

if __name__ == "__main__":
    main()