#!/usr/bin/env python3
"""
金融顾问学习脚本 - 银行业务模块
学习主题：银行存款产品与利息计算
"""

import os
from datetime import datetime

# 学习内容
learning_content = """
# 银行存款产品与利息计算

## 一、存款产品类型

### 1. 活期存款
- **定义**：不规定存期，可随时存取
- **利率**：0.2% - 0.3%（年利率）
- **特点**：流动性强，收益较低
- **适用**：日常资金周转

### 2. 定期存款
- **定义**：约定存期，到期支取
- **利率**：1.15% - 2.75%（根据存期）
- **存期选择**：3个月、6个月、1年、2年、3年、5年
- **提前支取**：按活期利率计息

### 3. 大额存单
- **起存金额**：20万元
- **利率优势**：比同期定期高0.3%-0.5%
- **流动性**：可转让、可质押
- **安全性**：受存款保险保障

### 4. 结构性存款
- **特点**：本金保障+浮动收益
- **挂钩标的**：汇率、利率、指数等
- **风险等级**：R1-R2（低风险）
- **收益区间**：0.5% - 5%（预期）

## 二、利息计算方法

### 单利计算
```
利息 = 本金 × 年利率 × 存期（年）
```

### 复利计算
```
本利和 = 本金 × (1 + 年利率)^年数
```

### 实际案例
**案例1**：10万元存3年定期，年利率2.75%
- 利息 = 100,000 × 2.75% × 3 = 8,250元
- 本利和 = 108,250元

**案例2**：10万元存大额存单3年，年利率3.2%
- 利息 = 100,000 × 3.2% × 3 = 9,600元
- 比普通定期多赚：1,350元

## 三、存款保险制度

### 保障范围
- **保额上限**：50万元（本金+利息）
- **保障银行**：所有吸收存款的银行业金融机构
- **偿付时限**：7个工作日内

### 注意事项
1. 同一家银行多个账户合并计算
2. 银行理财不属存款保险范围
3. 选择银行时注意是否参保

## 四、存款策略建议

### 分散原则
- 单家银行不超过50万
- 选择2-3家银行分散存放
- 活期+定期合理搭配

### 期限匹配
- 短期资金（1年内）：活期或短期定期
- 中期资金（1-3年）：中期定期或大额存单
- 长期资金（3年以上）：长期定期或国债

### 利率比较
- 不同银行利率差异可达0.5%
- 中小银行利率通常较高
- 关注银行促销活动期间

---
*学习时间：2026-03-29 07:10*
*主题：银行业务 - 存款产品*
"""

def save_learning():
    """保存学习内容"""
    ref_dir = os.path.expanduser("~/.openclaw/workspace/skills/finance-advisor/references")
    os.makedirs(ref_dir, exist_ok=True)
    
    filename = f"{ref_dir}/banking_deposit_20260329.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(learning_content)
    
    print(f"✅ 学习内容已保存: {filename}")
    
    # 更新轮换状态
    rotation_file = os.path.expanduser("~/.openclaw/workspace/memory/finance-rotation.json")
    import json
    with open(rotation_file, 'r') as f:
        data = json.load(f)
    
    # 轮换到下一个主题
    current_idx = data['sequence'].index(data['current'])
    next_idx = (current_idx + 1) % len(data['sequence'])
    data['current'] = data['sequence'][next_idx]
    data['lastUpdate'] = datetime.now().strftime('%Y-%m-%d')
    
    with open(rotation_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"🔄 下次学习主题: {data['current']}")
    
    return True

if __name__ == "__main__":
    print("📚 【金融顾问学习】银行业务 - 存款产品")
    print("=" * 50)
    save_learning()
    print("\n💡 关键要点:")
    print("• 大额存单20万起，利率比普通定期高0.3%-0.5%")
    print("• 存款保险保障上限50万元")
    print("• 单家银行分散，资金更安全")
    print("• 定期存款提前支取按活期计息")
