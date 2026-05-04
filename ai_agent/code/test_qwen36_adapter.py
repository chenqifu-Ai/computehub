"""测试 qwen3.6-35b 适配器流程"""

import sys, os, json
sys.path.insert(0, '/root/.openclaw/workspace')

print("=" * 60)
print("🧪 qwen3.6-35b 新 SOP 流程测试")
print("=" * 60)

# 步骤1: 需求分析
print("\n[步骤1/7] 🔍 需求分析")
test_question = "解释什么是机器学习"
print(f"  测试问题: {test_question}")

# 步骤2: 智能分析 - 查找文件
print("\n[步骤2/7] 📁 智能分析 - 文件查找")
# 铁律：先 git 查找
import subprocess
result = subprocess.run(
    ['git', 'ls-files', '|', 'grep', 'qwen36'],
    shell=True, capture_output=True, text=True, cwd='/root/.openclaw/workspace'
)
files = result.stdout.strip().split('\n')
print(f"  Git 查找结果: {len(files)} 个相关文件")
for f in files[:5]:
    if f: print(f"    - {f}")

# 步骤3: 代码生成 - 使用适配层
print("\n[步骤3/7] 💻 代码生成 - 适配层调用")
from ai_agent.config.qwen36_adapter import ask_code
print("  ✅ 适配层已导入")

# 步骤4: 自动执行
print("\n[步骤4/7] ⚡ 自动执行 - API调用")
try:
    result = ask_code("写一个Python函数，计算斐波那契数列前10项")
    print("  ✅ API调用成功")
    
    # 步骤5: 结果验证
    print("\n[步骤5/7] ✅ 结果验证")
    has_reasoning = hasattr(result, 'reasoning') and result.reasoning
    has_code = hasattr(result, 'code') and result.code
    has_answer = hasattr(result, 'answer') and result.answer
    print(f"    reasoning字段: {'✅ 存在' if has_reasoning else '❌ 缺失'}")
    print(f"    code字段: {'✅ 存在' if has_code else '❌ 缺失'}")
    print(f"    answer字段: {'✅ 存在' if has_answer else '❌ 缺失'}")
    
    # 步骤6: 学习优化
    print("\n[步骤6/7] 📚 学习优化")
    if has_code and has_reasoning:
        print("  ✅ 格式正确：reasoning 字段包含全部输出")
        print(f"  reasoning 长度: {len(result.reasoning)} 字符")
        print(f"  code 长度: {len(result.code)} 字符")
        
        # 步骤7: 连续交付 - 执行代码
        print("\n[步骤7/7] 🚀 连续交付 - 执行代码验证")
        exec(result.code, {'__builtins__': __builtins__})
        # 查找斐波那契函数并执行
        import types
        for name in dir():
            obj = eval(name)
            if isinstance(obj, types.FunctionType) and 'fib' in name.lower():
                try:
                    output = obj()
                    print(f"  函数 {name}() 输出: {output}")
                    print("  ✅ 代码执行验证通过")
                except Exception as e:
                    print(f"  ❌ 代码执行失败: {e}")
                    # 尝试直接执行
                    try:
                        exec(result.code)
                        for n in range(10):
                            try:
                                val = eval(f'fibonacci({n})')
                                print(f"    fibonacci({n}) = {val}")
                            except:
                                pass
                    except Exception as e2:
                        print(f"  直接执行也失败: {e2}")
    else:
        print("  ❌ 格式不符合预期")
        print(f"  result 属性: {dir(result)}")
        print(f"  result dict: {result.__dict__}")
        
except Exception as e:
    print(f"  ❌ 执行异常: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🧪 测试完成")
print("=" * 60)
