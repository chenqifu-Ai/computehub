#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalTokenHub - KYC/AML 合规模块
KYC/AML Compliance Module

创建时间：2026-04-19
作者：小智 (风控智能体)
版本：v1.0

功能:
- KYC 身份验证
- AML 反洗钱监控
- 制裁名单筛查
- 可疑交易报告
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KYCStatus(Enum):
    """KYC 状态"""
    PENDING = "pending"          # 待审核
    SUBMITTED = "submitted"      # 已提交
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    EXPIRED = "expired"          # 已过期
    UNDER_REVIEW = "under_review"  # 审核中


class KYCLevel(Enum):
    """KYC 等级"""
    LEVEL_0 = "level_0"  # 未认证
    LEVEL_1 = "level_1"  # 基础认证 (邮箱 + 手机)
    LEVEL_2 = "level_2"  # 身份认证 (身份证/护照)
    LEVEL_3 = "level_3"  # 高级认证 (地址证明 + 视频)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"          # 低风险
    MEDIUM = "medium"    # 中风险
    HIGH = "high"        # 高风险
    CRITICAL = "critical"  # 严重风险


class AlertType(Enum):
    """警报类型"""
    LARGE_TRANSACTION = "large_transaction"  # 大额交易
    FREQUENT_TRANSACTION = "frequent_transaction"  # 频繁交易
    SANCTIONS_MATCH = "sanctions_match"  # 制裁名单匹配
    PEP_MATCH = "pep_match"  # 政治公众人物匹配
    UNUSUAL_PATTERN = "unusual_pattern"  # 异常模式
    STRUCTURING = "structuring"  # 拆分交易


@dataclass
class KYCProfile:
    """KYC 档案"""
    user_id: str
    kyc_level: KYCLevel = KYCLevel.LEVEL_0
    status: KYCStatus = KYCStatus.PENDING
    first_name: str = ""
    last_name: str = ""
    id_type: str = ""  # passport, national_id, drivers_license
    id_number: str = ""
    id_expiry_date: Optional[datetime] = None
    nationality: str = ""
    date_of_birth: Optional[datetime] = None
    address: str = ""
    city: str = ""
    country: str = ""
    postal_code: str = ""
    phone_verified: bool = False
    email_verified: bool = False
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    rejection_reason: str = ""
    
    @property
    def is_verified(self) -> bool:
        """是否已认证"""
        return self.status == KYCStatus.APPROVED
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.id_expiry_date and datetime.now() > self.id_expiry_date:
            return True
        return False


@dataclass
class RiskScore:
    """风险评分"""
    user_id: str
    score: int = 0  # 0-100
    level: RiskLevel = RiskLevel.LOW
    factors: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_score(self, points: int, factor: str):
        """更新风险评分"""
        self.score = max(0, min(100, self.score + points))
        if factor not in self.factors:
            self.factors.append(factor)
        self.last_updated = datetime.now()
        self._update_level()
    
    def _update_level(self):
        """更新风险等级"""
        if self.score >= 80:
            self.level = RiskLevel.CRITICAL
        elif self.score >= 60:
            self.level = RiskLevel.HIGH
        elif self.score >= 40:
            self.level = RiskLevel.MEDIUM
        else:
            self.level = RiskLevel.LOW


@dataclass
class ComplianceAlert:
    """合规警报"""
    alert_id: str
    user_id: str
    alert_type: AlertType
    risk_level: RiskLevel
    description: str
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: str = "open"  # open, investigating, resolved, false_positive
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.alert_id is None:
            self.alert_id = str(uuid.uuid4())


class KYCAMLManager:
    """
    KYC/AML 合规管理器
    
    功能:
    - KYC 身份验证
    - 风险评分
    - 制裁名单筛查
    - 可疑交易监控
    - 合规报告
    """
    
    def __init__(self):
        """初始化合规管理器"""
        # 用户 KYC 档案 {user_id: KYCProfile}
        self.kyc_profiles: Dict[str, KYCProfile] = {}
        
        # 用户风险评分 {user_id: RiskScore}
        self.risk_scores: Dict[str, RiskScore] = {}
        
        # 合规警报
        self.alerts: List[ComplianceAlert] = []
        
        # 制裁名单 (简化版)
        self.sanctions_list = self._load_sanctions_list()
        
        # PEP 名单 (政治公众人物)
        self.pep_list = self._load_pep_list()
        
        # 交易限额 (基于 KYC 等级)
        self.limits = {
            KYCLevel.LEVEL_0: {
                'daily_deposit': 1000,
                'daily_withdrawal': 0,
                'daily_trade': 0
            },
            KYCLevel.LEVEL_1: {
                'daily_deposit': 10000,
                'daily_withdrawal': 5000,
                'daily_trade': 50000
            },
            KYCLevel.LEVEL_2: {
                'daily_deposit': 100000,
                'daily_withdrawal': 50000,
                'daily_trade': 500000
            },
            KYCLevel.LEVEL_3: {
                'daily_deposit': float('inf'),
                'daily_withdrawal': float('inf'),
                'daily_trade': float('inf')
            }
        }
        
        # 警报阈值
        self.alert_thresholds = {
            'large_transaction_usd': 10000,
            'frequent_transactions_count': 10,
            'frequent_transactions_hours': 24,
            'structuring_threshold': 0.9  # 接近限额 90%
        }
        
        logger.info("KYC/AML 合规管理器已初始化")
    
    def _load_sanctions_list(self) -> List[str]:
        """加载制裁名单 (简化版)"""
        # 实际应该从 OFAC/UN/EU 等官方名单加载
        return [
            "sanctioned_entity_1",
            "sanctioned_entity_2"
        ]
    
    def _load_pep_list(self) -> List[str]:
        """加载 PEP 名单 (简化版)"""
        return [
            "pep_person_1",
            "pep_person_2"
        ]
    
    def create_kyc_profile(self, user_id: str) -> KYCProfile:
        """
        创建 KYC 档案
        
        Args:
            user_id: 用户 ID
        
        Returns:
            KYCProfile 对象
        """
        if user_id in self.kyc_profiles:
            return self.kyc_profiles[user_id]
        
        profile = KYCProfile(user_id=user_id)
        self.kyc_profiles[user_id] = profile
        
        # 初始化风险评分
        self.risk_scores[user_id] = RiskScore(user_id=user_id)
        
        logger.info(f"为用户 {user_id} 创建 KYC 档案")
        
        return profile
    
    def submit_kyc(self, user_id: str, kyc_data: Dict) -> Tuple[bool, str]:
        """
        提交 KYC 信息
        
        Args:
            user_id: 用户 ID
            kyc_data: KYC 数据
        
        Returns:
            (success, message)
        """
        profile = self.kyc_profiles.get(user_id)
        if not profile:
            profile = self.create_kyc_profile(user_id)
        
        # 更新 KYC 信息
        profile.first_name = kyc_data.get('first_name', '')
        profile.last_name = kyc_data.get('last_name', '')
        profile.id_type = kyc_data.get('id_type', '')
        profile.id_number = kyc_data.get('id_number', '')
        profile.nationality = kyc_data.get('nationality', '')
        profile.country = kyc_data.get('country', '')
        profile.address = kyc_data.get('address', '')
        
        # 设置 KYC 等级
        if profile.id_number:
            profile.kyc_level = KYCLevel.LEVEL_2
        
        profile.status = KYCStatus.SUBMITTED
        profile.submitted_at = datetime.now()
        
        logger.info(f"用户 {user_id} 提交 KYC 信息")
        
        return True, "KYC 信息已提交，等待审核"
    
    def approve_kyc(self, user_id: str, reviewed_by: str, kyc_level: KYCLevel = KYCLevel.LEVEL_2) -> Tuple[bool, str]:
        """
        批准 KYC
        
        Args:
            user_id: 用户 ID
            reviewed_by: 审核人
            kyc_level: KYC 等级
        
        Returns:
            (success, message)
        """
        profile = self.kyc_profiles.get(user_id)
        if not profile:
            return False, "KYC 档案不存在"
        
        profile.status = KYCStatus.APPROVED
        profile.kyc_level = kyc_level
        profile.approved_at = datetime.now()
        profile.reviewed_by = reviewed_by
        
        # 更新风险评分
        if user_id in self.risk_scores:
            self.risk_scores[user_id].update_score(-10, "kyc_approved")
        
        logger.info(f"用户 {user_id} KYC 已批准，等级：{kyc_level.value}")
        
        return True, "KYC 已批准"
    
    def reject_kyc(self, user_id: str, reason: str, reviewed_by: str) -> Tuple[bool, str]:
        """
        拒绝 KYC
        
        Args:
            user_id: 用户 ID
            reason: 拒绝原因
            reviewed_by: 审核人
        
        Returns:
            (success, message)
        """
        profile = self.kyc_profiles.get(user_id)
        if not profile:
            return False, "KYC 档案不存在"
        
        profile.status = KYCStatus.REJECTED
        profile.rejection_reason = reason
        profile.reviewed_by = reviewed_by
        
        # 更新风险评分
        if user_id in self.risk_scores:
            self.risk_scores[user_id].update_score(20, "kyc_rejected")
        
        logger.info(f"用户 {user_id} KYC 被拒绝：{reason}")
        
        return True, f"KYC 被拒绝：{reason}"
    
    def check_sanctions(self, name: str) -> Tuple[bool, str]:
        """
        制裁名单筛查
        
        Args:
            name: 姓名
        
        Returns:
            (match, details)
        """
        # 简化版：直接匹配
        if name.lower() in [s.lower() for s in self.sanctions_list]:
            return True, f"制裁名单匹配：{name}"
        
        # 模糊匹配 (简化版)
        for sanctioned in self.sanctions_list:
            if name.lower() in sanctioned.lower() or sanctioned.lower() in name.lower():
                return True, f"制裁名单模糊匹配：{name}"
        
        return False, "无制裁名单匹配"
    
    def check_pep(self, name: str) -> Tuple[bool, str]:
        """
        PEP 筛查
        
        Args:
            name: 姓名
        
        Returns:
            (match, details)
        """
        if name.lower() in [p.lower() for p in self.pep_list]:
            return True, f"PEP 名单匹配：{name}"
        
        return False, "无 PEP 名单匹配"
    
    def monitor_transaction(self, user_id: str, amount: float, currency: str, tx_type: str) -> List[ComplianceAlert]:
        """
        监控交易
        
        Args:
            user_id: 用户 ID
            amount: 金额
            currency: 币种
            tx_type: 交易类型
        
        Returns:
            生成的警报列表
        """
        alerts = []
        
        # 获取风险评分
        risk_score = self.risk_scores.get(user_id, RiskScore(user_id=user_id))
        
        # 大额交易监控
        if amount >= self.alert_thresholds['large_transaction_usd']:
            alert = ComplianceAlert(
                alert_id=None,
                user_id=user_id,
                alert_type=AlertType.LARGE_TRANSACTION,
                risk_level=RiskLevel.MEDIUM,
                description=f"大额交易：{amount} {currency}",
                amount=amount,
                currency=currency
            )
            alerts.append(alert)
            self.alerts.append(alert)
            
            # 更新风险评分
            risk_score.update_score(5, "large_transaction")
            
            logger.info(f"大额交易警报：{user_id} - {amount} {currency}")
        
        # 制裁名单筛查 (如果是新用户或高风险地区)
        if risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            profile = self.kyc_profiles.get(user_id)
            if profile:
                match, details = self.check_sanctions(f"{profile.first_name} {profile.last_name}")
                if match:
                    alert = ComplianceAlert(
                        alert_id=None,
                        user_id=user_id,
                        alert_type=AlertType.SANCTIONS_MATCH,
                        risk_level=RiskLevel.CRITICAL,
                        description=details,
                        amount=amount,
                        currency=currency
                    )
                    alerts.append(alert)
                    self.alerts.append(alert)
                    
                    risk_score.update_score(50, "sanctions_match")
                    
                    logger.warning(f"制裁名单匹配警报：{user_id} - {details}")
        
        return alerts
    
    def get_user_limits(self, user_id: str) -> Dict:
        """
        获取用户限额
        
        Args:
            user_id: 用户 ID
        
        Returns:
            限额信息
        """
        profile = self.kyc_profiles.get(user_id)
        if not profile:
            return self.limits[KYCLevel.LEVEL_0]
        
        return self.limits.get(profile.kyc_level, self.limits[KYCLevel.LEVEL_0])
    
    def check_transaction_limit(self, user_id: str, amount: float, tx_type: str) -> Tuple[bool, str]:
        """
        检查交易限额
        
        Args:
            user_id: 用户 ID
            amount: 金额
            tx_type: 交易类型 (deposit/withdrawal/trade)
        
        Returns:
            (allowed, message)
        """
        limits = self.get_user_limits(user_id)
        
        limit_key = f"daily_{tx_type}"
        limit = limits.get(limit_key, 0)
        
        if amount > limit:
            return False, f"超过{tx_type}限额：{limit}"
        
        return True, "交易在限额内"
    
    def get_user_risk_score(self, user_id: str) -> Dict:
        """
        获取用户风险评分
        
        Args:
            user_id: 用户 ID
        
        Returns:
            风险评分信息
        """
        score = self.risk_scores.get(user_id)
        if not score:
            return {"error": "风险评分不存在"}
        
        return {
            "user_id": user_id,
            "score": score.score,
            "level": score.level.value,
            "factors": score.factors,
            "last_updated": score.last_updated.isoformat()
        }
    
    def get_alerts(self, status: str = "open", limit: int = 50) -> List[Dict]:
        """
        获取警报
        
        Args:
            status: 警报状态
            limit: 数量限制
        
        Returns:
            警报列表
        """
        filtered = [a for a in self.alerts if a.status == status]
        filtered.sort(key=lambda x: x.created_at, reverse=True)
        
        return [
            {
                "alert_id": a.alert_id,
                "user_id": a.user_id,
                "type": a.alert_type.value,
                "risk_level": a.risk_level.value,
                "description": a.description,
                "amount": a.amount,
                "currency": a.currency,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            }
            for a in filtered[:limit]
        ]
    
    def resolve_alert(self, alert_id: str, resolved_by: str, notes: str = "", is_false_positive: bool = False) -> Tuple[bool, str]:
        """
        解决警报
        
        Args:
            alert_id: 警报 ID
            resolved_by: 解决人
            notes: 备注
            is_false_positive: 是否误报
        
        Returns:
            (success, message)
        """
        alert = next((a for a in self.alerts if a.alert_id == alert_id), None)
        if not alert:
            return False, "警报不存在"
        
        alert.status = "false_positive" if is_false_positive else "resolved"
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        alert.notes = notes
        
        # 如果是误报，降低风险评分
        if is_false_positive and alert.user_id in self.risk_scores:
            self.risk_scores[alert.user_id].update_score(-5, "false_positive")
        
        logger.info(f"警报已解决：{alert_id} by {resolved_by}")
        
        return True, "警报已解决"
    
    def get_compliance_report(self, days: int = 30) -> Dict:
        """
        生成合规报告
        
        Args:
            days: 天数
        
        Returns:
            合规报告
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_alerts = [a for a in self.alerts if a.created_at >= cutoff]
        
        # 统计
        total_alerts = len(recent_alerts)
        open_alerts = len([a for a in recent_alerts if a.status == "open"])
        resolved_alerts = len([a for a in recent_alerts if a.status == "resolved"])
        
        # 按类型统计
        by_type = {}
        for alert in recent_alerts:
            type_name = alert.alert_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # 按风险等级统计
        by_risk = {}
        for alert in recent_alerts:
            level = alert.risk_level.value
            by_risk[level] = by_risk.get(level, 0) + 1
        
        return {
            "period_days": days,
            "total_alerts": total_alerts,
            "open_alerts": open_alerts,
            "resolved_alerts": resolved_alerts,
            "by_type": by_type,
            "by_risk_level": by_risk,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        """获取合规统计"""
        total_users = len(self.kyc_profiles)
        verified_users = len([p for p in self.kyc_profiles.values() if p.is_verified])
        pending_reviews = len([p for p in self.kyc_profiles.values() if p.status == KYCStatus.SUBMITTED])
        open_alerts = len([a for a in self.alerts if a.status == "open"])
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "verification_rate": f"{verified_users/total_users*100:.1f}%" if total_users > 0 else "0%",
            "pending_reviews": pending_reviews,
            "open_alerts": open_alerts,
            "total_alerts": len(self.alerts),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """测试主函数"""
    print("=" * 60)
    print("⚖️ GlobalTokenHub - KYC/AML 合规测试")
    print("=" * 60)
    
    # 创建合规管理器
    manager = KYCAMLManager()
    
    print("\n✅ KYC/AML 管理器初始化完成")
    
    # 创建 KYC 档案
    print("\n📋 创建 KYC 档案...")
    profile1 = manager.create_kyc_profile("user_001")
    profile2 = manager.create_kyc_profile("user_002")
    
    # 提交 KYC
    print("\n📝 提交 KYC 信息...")
    success, msg = manager.submit_kyc("user_001", {
        'first_name': 'John',
        'last_name': 'Doe',
        'id_type': 'passport',
        'id_number': 'AB123456',
        'nationality': 'US',
        'country': 'United States'
    })
    print(f"  user_001 KYC 提交：{'✅' if success else '❌'} - {msg}")
    
    # 批准 KYC
    print("\n✅ 批准 KYC...")
    success, msg = manager.approve_kyc("user_001", "compliance_officer_1", KYCLevel.LEVEL_2)
    print(f"  user_001 KYC 批准：{'✅' if success else '❌'} - {msg}")
    
    # 检查限额
    print("\n💰 检查交易限额...")
    limits = manager.get_user_limits("user_001")
    print(f"  user_001 限额:")
    print(f"    日充值：${limits['daily_deposit']:,.0f}")
    print(f"    日提现：${limits['daily_withdrawal']:,.0f}")
    print(f"    日交易：${limits['daily_trade']:,.0f}")
    
    # 监控交易
    print("\n🔍 监控交易...")
    alerts = manager.monitor_transaction("user_001", 15000.0, "USDT", "deposit")
    print(f"  大额交易警报：{len(alerts)} 个")
    
    # 风险评分
    print("\n📊 风险评分...")
    risk = manager.get_user_risk_score("user_001")
    print(f"  user_001 风险评分：{risk.get('score', 0)} ({risk.get('level', 'unknown')})")
    
    # 合规统计
    print("\n📈 合规统计...")
    stats = manager.get_stats()
    print(f"  总用户数：{stats['total_users']}")
    print(f"  已认证用户：{stats['verified_users']}")
    print(f"  认证率：{stats['verification_rate']}")
    print(f"  待审核：{stats['pending_reviews']}")
    print(f"  未解决警报：{stats['open_alerts']}")
    
    # 合规报告
    print("\n📋 合规报告...")
    report = manager.get_compliance_report(days=30)
    print(f"  30 天内警报总数：{report['total_alerts']}")
    print(f"  未解决：{report['open_alerts']}")
    print(f"  已解决：{report['resolved_alerts']}")
    
    print("\n" + "=" * 60)
    print("✅ KYC/AML 合规测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
