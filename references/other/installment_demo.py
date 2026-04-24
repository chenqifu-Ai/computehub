#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分期付款计算器 - 根据记忆重写
支持等额本息、等额本金两种计算方式
"""

def calculate_installment(principal, annual_rate, months, method="等额本息"):
    """
    计算分期付款
    :param principal: 本金
    :param annual_rate: 年利率
    :param months: 分期月数
    :param method: 计算方式 "等额本息" 或 "等额本金"
    :return: 每月还款详情列表
    """
    monthly_rate = annual_rate / 12 / 100  # 月利率
    
    if method == "等额本息":
        # 等额本息公式: 每月还款额 = [本金×月利率×(1+月利率)^还款月数] ÷ [(1+月利率)^还款月数-1]
        monthly_payment = principal * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
        
        results = []
        remaining = principal
        total_interest = 0
        
        for month in range(1, months + 1):
            interest = remaining * monthly_rate
            principal_part = monthly_payment - interest
            remaining -= principal_part
            total_interest += interest
            
            results.append({
                "期数": month,
                "月供": round(monthly_payment, 2),
                "本金": round(principal_part, 2),
                "利息": round(interest, 2),
                "剩余本金": round(remaining, 2)
            })
        
        return results, round(monthly_payment, 2), round(total_interest, 2)
    
    elif method == "等额本金":
        # 等额本金: 每月还本金固定，利息逐月减少
        monthly_principal = principal / months
        
        results = []
        remaining = principal
        total_interest = 0
        
        for month in range(1, months + 1):
            interest = remaining * monthly_rate
            monthly_payment = monthly_principal + interest
            remaining -= monthly_principal
            total_interest += interest
            
            results.append({
                "期数": month,
                "月供": round(monthly_payment, 2),
                "本金": round(monthly_principal, 2),
                "利息": round(interest, 2),
                "剩余本金": round(remaining, 2)
            })
        
        return results, None, round(total_interest, 2)

def main():
    """演示分期计算"""
    print("📊 分期付款计算器")
    print("=" * 50)
    
    # 示例：借款10万，年利率5%，分12期
    principal = 100000
    annual_rate = 5.0
    months = 12
    
    # 等额本息计算
    print(f"\n💳 等额本息计算 (本金: {principal}, 年利率: {annual_rate}%, 期数: {months})")
    results, monthly_payment, total_interest = calculate_installment(principal, annual_rate, months, "等额本息")
    
    print(f"每月还款: ¥{monthly_payment}")
    print(f"总利息: ¥{total_interest}")
    print(f"总还款: ¥{principal + total_interest}")
    
    # 等额本金计算
    print(f"\n💳 等额本金计算 (本金: {principal}, 年利率: {annual_rate}%, 期数: {months})")
    results, _, total_interest = calculate_installment(principal, annual_rate, months, "等额本金")
    
    print(f"总利息: ¥{total_interest}")
    print(f"总还款: ¥{principal + total_interest}")
    
    # 显示前3期详情
    print("\n📈 前3期还款详情:")
    for i in range(3):
        print(f"第{results[i]['期数']}期: 月供¥{results[i]['月供']} (本金¥{results[i]['本金']} + 利息¥{results[i]['利息']})")

if __name__ == "__main__":
    main()