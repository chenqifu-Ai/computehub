#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控部检查脚本
执行内容合规性扫描、版权风险检查、平台政策更新监控、风险预警报告生成
"""

import os
import re
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any

class RiskControlChecker:
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "content_compliance": {"status": "pending", "issues": [], "scanned_files": 0},
            "copyright_risk": {"status": "pending", "issues": [], "scanned_files": 0},
            "policy_monitoring": {"status": "pending", "updates": [], "checked_policies": 0},
            "risk_warning": {"status": "pending", "warnings": []}
        }
        
        # 合规性关键词
        self.compliance_keywords = [
            # 敏感内容
            r'赌博|赌场|赌球|赌马',
            r'色情|黄色|成人|av|porn',
            r'暴力|血腥|恐怖',
            r'毒品|吸毒|贩毒',
            r'传销|金字塔|庞氏骗局',
            r'诈骗|骗局|钓鱼',
            
            # 政治敏感
            r'领导人姓名',  # 实际使用时需要具体化
            r'政府机密',
            r'国家秘密',
            
            # 商业违规
            r'内幕交易|操纵市场',
            r'虚假宣传|夸大其词',
            r'不正当竞争',
            
            # 个人信息
            r'身份证号|\d{17}[0-9X]',
            r'手机号|1[3-9]\d{9}',
            r'银行卡号|\d{16,19}',
            r'密码|口令|secret|password',
        ]
        
        # 版权风险关键词
        self.copyright_keywords = [
            r'版权所有|©|copyright',
            r'侵权|盗版|破解',
            r'未经授权',
            r'转载需注明',
            r'原创内容',
        ]
        
        # 文件扩展名白名单
        self.scan_extensions = ['.md', '.txt', '.py', '.js', '.html', '.css', '.json']
    
    def scan_content_compliance(self) -> Dict[str, Any]:
        """扫描内容合规性"""
        print("🔍 开始内容合规性扫描...")
        
        issues = []
        scanned_count = 0
        
        for root, _, files in os.walk(self.workspace_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.scan_extensions):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        scanned_count += 1
                        
                        # 检查合规性关键词
                        for pattern in self.compliance_keywords:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                issues.append({
                                    "file": str(file_path.relative_to(self.workspace_path)),
                                    "issue": f"发现敏感内容: {match.group()}",
                                    "context": content[max(0, match.start()-50):match.end()+50],
                                    "severity": "high"
                                })
                        
                    except (UnicodeDecodeError, PermissionError, OSError):
                        continue
        
        status = "pass" if not issues else "fail"
        
        return {
            "status": status,
            "issues": issues,
            "scanned_files": scanned_count
        }
    
    def check_copyright_risk(self) -> Dict[str, Any]:
        """检查版权风险"""
        print("🔍 开始版权风险检查...")
        
        issues = []
        scanned_count = 0
        
        for root, _, files in os.walk(self.workspace_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.scan_extensions):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        scanned_count += 1
                        
                        # 检查版权声明
                        copyright_pattern = r'(?i)(copyright|版权所有|©)[\s:：]*([\d]{4}[\s-]*[\d]{4})?[\s]*([^\n]+)'
                        matches = re.finditer(copyright_pattern, content)
                        
                        for match in matches:
                            issues.append({
                                "file": str(file_path.relative_to(self.workspace_path)),
                                "issue": f"发现版权声明: {match.group()}",
                                "context": content[max(0, match.start()-30):match.end()+30],
                                "severity": "medium"
                            })
                        
                        # 检查侵权风险内容
                        for pattern in self.copyright_keywords:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                issues.append({
                                    "file": str(file_path.relative_to(self.workspace_path)),
                                    "issue": f"版权相关内容: {match.group()}",
                                    "context": content[max(0, match.start()-30):match.end()+30],
                                    "severity": "low"
                                })
                        
                    except (UnicodeDecodeError, PermissionError, OSError):
                        continue
        
        status = "pass" if len(issues) == 0 else "warning"
        
        return {
            "status": status,
            "issues": issues,
            "scanned_files": scanned_count
        }
    
    def monitor_policy_updates(self) -> Dict[str, Any]:
        """监控平台政策更新"""
        print("🔍 开始平台政策更新监控...")
        
        updates = []
        checked_count = 0
        
        # 检查政策相关文件
        policy_files = [
            "AGENTS.md", "SOUL.md", "SOP.md", "TOOLS.md", "USER.md",
            "HEARTBEAT.md", "MEMORY.md"
        ]
        
        for policy_file in policy_files:
            file_path = self.workspace_path / policy_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    checked_count += 1
                    
                    # 检查最近修改时间
                    mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                    if (datetime.datetime.now() - mtime).days < 7:
                        updates.append({
                            "file": policy_file,
                            "last_modified": mtime.isoformat(),
                            "change_type": "recent_update",
                            "description": f"文件最近7天内被修改"
                        })
                        
                    # 检查政策关键词
                    policy_keywords = [
                        r'合规|compliance',
                        r'政策|policy',
                        r'规则|rule',
                        r'风险|risk',
                        r'安全|security',
                        r'隐私|privacy'
                    ]
                    
                    for pattern in policy_keywords:
                        if re.search(pattern, content, re.IGNORECASE):
                            updates.append({
                                "file": policy_file,
                                "last_modified": mtime.isoformat(),
                                "change_type": "policy_content",
                                "description": f"包含政策相关关键词"
                            })
                            break
                            
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
        
        return {
            "status": "completed",
            "updates": updates,
            "checked_policies": checked_count
        }
    
    def generate_risk_warnings(self) -> Dict[str, Any]:
        """生成风险预警报告"""
        print("⚠️  生成风险预警报告...")
        
        warnings = []
        
        # 基于扫描结果生成预警
        if self.results["content_compliance"]["status"] == "fail":
            warnings.append({
                "level": "high",
                "type": "content_compliance",
                "description": "发现敏感内容合规问题，需要立即处理",
                "affected_files": len(self.results["content_compliance"]["issues"])
            })
        
        if self.results["copyright_risk"]["status"] == "warning":
            warnings.append({
                "level": "medium",
                "type": "copyright_risk",
                "description": "发现版权相关风险内容，建议审查",
                "affected_files": len(self.results["copyright_risk"]["issues"])
            })
        
        # 检查是否有近期政策更新
        recent_updates = [u for u in self.results["policy_monitoring"]["updates"] 
                         if u["change_type"] == "recent_update"]
        if recent_updates:
            warnings.append({
                "level": "low",
                "type": "policy_update",
                "description": f"检测到{len(recent_updates)}个政策文件近期更新",
                "affected_files": len(recent_updates)
            })
        
        # 如果没有发现问题，添加正常状态
        if not warnings:
            warnings.append({
                "level": "info",
                "type": "all_clear",
                "description": "风控检查通过，未发现重大风险",
                "affected_files": 0
            })
        
        return {
            "status": "completed",
            "warnings": warnings
        }
    
    def run_full_check(self) -> Dict[str, Any]:
        """执行完整风控检查"""
        print("🚀 开始执行风控部全面检查...")
        print("=" * 60)
        
        # 执行各项检查
        self.results["content_compliance"] = self.scan_content_compliance()
        self.results["copyright_risk"] = self.check_copyright_risk()
        self.results["policy_monitoring"] = self.monitor_policy_updates()
        self.results["risk_warning"] = self.generate_risk_warnings()
        
        print("=" * 60)
        print("✅ 风控检查完成!")
        
        return self.results
    
    def save_report(self, output_path: str = None) -> str:
        """保存检查报告"""
        if output_path is None:
            output_dir = self.workspace_path / "reports" / "risk_control"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"risk_control_report_{timestamp}.json"
        else:
            output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        return str(output_path)
    
    def generate_summary(self) -> str:
        """生成摘要报告"""
        summary = []
        summary.append("📊 风控检查摘要报告")
        summary.append("=" * 40)
        
        # 内容合规性
        comp = self.results["content_compliance"]
        summary.append(f"🔍 内容合规性: {comp['status'].upper()}")
        summary.append(f"   扫描文件: {comp['scanned_files']} 个")
        summary.append(f"   发现问题: {len(comp['issues'])} 个")
        
        # 版权风险
        copyr = self.results["copyright_risk"]
        summary.append(f"📚 版权风险: {copyr['status'].upper()}")
        summary.append(f"   扫描文件: {copyr['scanned_files']} 个")
        summary.append(f"   发现问题: {len(copyr['issues'])} 个")
        
        # 政策监控
        policy = self.results["policy_monitoring"]
        summary.append(f"📋 政策监控: {policy['status'].upper()}")
        summary.append(f"   检查政策: {policy['checked_policies']} 个")
        summary.append(f"   更新情况: {len(policy['updates'])} 个")
        
        # 风险预警
        warnings = self.results["risk_warning"]
        summary.append(f"⚠️  风险预警: {len(warnings['warnings'])} 个警告")
        for warning in warnings['warnings']:
            summary.append(f"   [{warning['level'].upper()}] {warning['description']}")
        
        summary.append("=" * 40)
        summary.append(f"检查时间: {self.results['timestamp']}")
        
        return "\n".join(summary)

def main():
    """主函数"""
    checker = RiskControlChecker()
    
    # 执行检查
    results = checker.run_full_check()
    
    # 保存报告
    report_path = checker.save_report()
    print(f"📄 报告已保存至: {report_path}")
    
    # 输出摘要
    print("\n" + checker.generate_summary())
    
    # 如果有问题，显示详细信息
    if results["content_compliance"]["issues"]:
        print("\n❌ 内容合规性问题详情:")
        for issue in results["content_compliance"]["issues"]:
            print(f"   📍 {issue['file']}: {issue['issue']}")
    
    if results["copyright_risk"]["issues"]:
        print("\n⚠️  版权风险问题详情:")
        for issue in results["copyright_risk"]["issues"]:
            print(f"   📍 {issue['file']}: {issue['issue']}")

if __name__ == "__main__":
    main()