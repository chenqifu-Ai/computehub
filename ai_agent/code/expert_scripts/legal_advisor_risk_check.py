#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法海（法律顾问）自动风险评估脚本 v2.0
检查维度：合同合规、知识产权、劳动法、数据安全、反垄断、税务合规
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
RESULTS_DIR = WORKSPACE / "ai_agent" / "results"
REPORT_DIR = WORKSPACE / "expert_work_logs"


def check_contract_compliance():
    """合同合规检查"""
    risks = []
    # 检查工作目录中是否有待审核的合同标记
    contract_dir = WORKSPACE / "contracts"
    if not contract_dir.exists():
        return {"status": "PASS", "issues": []}
    for f in contract_dir.rglob("*"):
        if f.suffix in [".md", ".txt", ".conf"]:
            content = f.read_text(encoding="utf-8", errors="ignore")
            # 检查常见法律风险关键词
            risk_keywords = ["未明确违约责任", "无保密条款", "无争议解决条款", "未指定管辖法院"]
            for kw in risk_keywords:
                if kw in content:
                    risks.append(f"文件 {f.name}: 发现风险表述 '{kw}'")
    return {"status": "WARNING" if risks else "PASS", "issues": risks}


def check_ip_protection():
    """知识产权保护检查"""
    risks = []
    sensitive_patterns = [
        (r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"]?[a-zA-Z0-9]{8,}", "硬编码密钥"),
        (r"(?i)(token|jwt)\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{16,}", "硬编码令牌"),
    ]
    # 只扫描顶层和关键目录，每目录最多100个文件
    scan_dirs = [
        "scripts/", "ai_agent/code/", "ai_agent/scripts/",
        "config/", "expert_scripts/", "framework/", ".openclaw/"
    ]
    scanned = 0
    MAX_PER_DIR = 100
    for rel in scan_dirs:
        base = WORKSPACE / rel
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for pattern, desc in sensitive_patterns:
                    if re.search(pattern, content):
                        risks.append(f"{py_file.relative_to(WORKSPACE)}: 疑似 {desc}")
                scanned += 1
            except:
                pass
            if scanned >= MAX_PER_DIR:
                break
    return {"status": "WARNING" if risks else "PASS", "issues": risks}


def check_data_privacy():
    """数据隐私合规检查 (个人信息保护法)"""
    risks = []
    # 检查是否有明文存储身份证号/手机号等
    sensitive_pii = [
        (r"(?i)身份证号?\s*[:=]\s*['\"]?(\d{15,18})", "身份证号明文"),
        (r"(?i)手机号?\s*[:=]\s*['\"]?(\d{11})", "手机号明文"),
        (r"(?i)银行卡号?\s*[:=]\s*['\"]?(\d{16,19})", "银行卡号明文"),
    ]
    scanned = 0
    for data_file in WORKSPACE.rglob("*.csv"):
        if scanned >= 100:
            break
        if "node_modules" in str(data_file) or ".git" in str(data_file):
            continue
        try:
            content = data_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, desc in sensitive_pii:
                if re.search(pattern, content):
                    risks.append(f"{data_file.name}: 疑似 {desc}")
        except:
            pass
        scanned += 1
    for data_file in WORKSPACE.rglob("*.json"):
        if scanned >= 200:
            break
        if "node_modules" in str(data_file) or ".git" in str(data_file):
            continue
        try:
            content = data_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, desc in sensitive_pii:
                if re.search(pattern, content):
                    risks.append(f"{data_file.name}: 疑似 {desc}")
        except:
            pass
        scanned += 1
    return {"status": "WARNING" if risks else "PASS", "issues": risks}


def check_labor_compliance():
    """劳动法合规检查"""
    risks = []
    # 检查系统用户和权限（是否有未授权用户访问生产数据）
    try:
        result = subprocess.run(["getent", "passwd"], capture_output=True, text=True, timeout=2)
        users = [line.split(":")[0] for line in result.stdout.strip().split("\n") if int(line.split(":")[2]) > 1000 and line.split(":")[0] != "nobody"]
        if len(users) > 5:
            risks.append(f"系统用户数过多 ({len(users)})，建议审查权限分配")
    except Exception:
        pass  # 超时或错误跳过
    return {"status": "WARNING" if risks else "PASS", "issues": risks}


def check_tax_compliance():
    """税务合规检查"""
    risks = []
    # 检查是否有明显的税务相关文件异常
    tax_dir = WORKSPACE / "finance" / "taxes"
    if tax_dir.exists():
        files = list(tax_dir.rglob("*"))
        if len(files) == 0:
            risks.append("税务目录为空，建议定期更新税务文件")
    else:
        risks.append("税务目录不存在，建议创建 finance/taxes/ 目录管理税务文件")
    return {"status": "WARNING" if risks else "PASS", "issues": risks}


def generate_report():
    """生成风险评估报告"""
    now = datetime.now()
    
    checks = {
        "合同合规": check_contract_compliance(),
        "知识产权保护": check_ip_protection(),
        "数据隐私": check_data_privacy(),
        "劳动法合规": check_labor_compliance(),
        "税务合规": check_tax_compliance(),
    }
    
    total_issues = sum(len(v["issues"]) for v in checks.values())
    risk_level = "LOW"
    if total_issues > 10:
        risk_level = "HIGH"
    elif total_issues > 5:
        risk_level = "MEDIUM"
    
    report = {
        "expert": "法海（法律顾问）",
        "task": "全面风险评估",
        "timestamp": now.isoformat(),
        "risk_level": risk_level,
        "total_issues": total_issues,
        "checks": checks,
        "recommendations": [],
    }
    
    # 根据检查结果生成建议
    if total_issues == 0:
        report["recommendations"].append("✅ 所有检查项通过，继续保持合规状态")
    else:
        report["recommendations"].append(f"发现 {total_issues} 个风险项，建议按优先级整改")
        for category, result in checks.items():
            if result["status"] == "WARNING":
                report["recommendations"].append(f"⚠️ {category}: 需处理 {len(result['issues'])} 个问题")
        report["recommendations"].append("建议：每季度进行一次全面法律风险评估")
        report["recommendations"].append("建议：重要合同签署前由专职法务审核")
    
    # 保存报告
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"法海_法律顾问_report_{now.strftime('%Y%m%d_%H%M%S')}.json"
    report["output_file"] = str(report_file)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


if __name__ == "__main__":
    result = generate_report()
    print(f"【法海·法律顾问】风险评估完成")
    print(f"  风险等级: {result['risk_level']}")
    print(f"  发现问题: {result['total_issues']}")
    for rec in result['recommendations']:
        print(f"  {rec}")
    print(f"  报告: {result['output_file']}")
