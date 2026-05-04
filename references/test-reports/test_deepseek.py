#!/usr/bin/env python3
"""
测试 ollama-cloud/deepseek-v3.1:671b 模型性能
"""

def fibonacci(n):
    """计算斐波那契数列的前n项"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    return fib

def test_fibonacci():
    """测试斐波那契函数"""
    print("🧪 测试 ollama-cloud/deepseek-v3.1:671b 模型")
    print("=" * 50)
    
    # 测试不同长度的斐波那契数列
    test_cases = [5, 10, 15]
    
    for n in test_cases:
        result = fibonacci(n)
        print(f"斐波那契数列前{n}项: {result}")
        
        # 验证结果
        if len(result) == n:
            print(f"✅ 长度验证通过: {len(result)}项")
        else:
            print(f"❌ 长度验证失败: 期望{n}, 实际{len(result)}")
        
        # 验证斐波那契规则
        valid = True
        for i in range(2, len(result)):
            if result[i] != result[i-1] + result[i-2]:
                valid = False
                break
        
        if valid:
            print("✅ 斐波那契规则验证通过")
        else:
            print("❌ 斐波那契规则验证失败")
        
        print("-" * 30)
    
    print("🎯 测试完成！")

if __name__ == "__main__":
    test_fibonacci()