#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalTokenHub - 钱包管理模块
Wallet Management Module

创建时间：2026-04-19
作者：小智 (财务智能体)
版本：v1.0

功能:
- 多币种钱包管理
- 充值/提现处理
- 冷热钱包分离
- 交易密码验证
"""

import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WalletType(Enum):
    """钱包类型"""
    HOT = "hot"      # 热钱包 (在线)
    COLD = "cold"    # 冷钱包 (离线)
    FUND = "fund"    # 资金池


class TransactionType(Enum):
    """交易类型"""
    DEPOSIT = "deposit"      # 充值
    WITHDRAWAL = "withdrawal"  # 提现
    TRANSFER = "transfer"    # 转账
    TRADE = "trade"          # 交易


class TransactionStatus(Enum):
    """交易状态"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


@dataclass
class Wallet:
    """钱包数据结构"""
    wallet_id: str
    user_id: str
    currency: str  # 币种 (BTC, USDT, ETH 等)
    balance: float = 0.0
    available_balance: float = 0.0  # 可用余额
    frozen_balance: float = 0.0  # 冻结余额
    wallet_type: WalletType = WalletType.HOT
    address: str = ""  # 充值地址
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.wallet_id is None:
            self.wallet_id = str(uuid.uuid4())
        if self.address is None or self.address == "":
            self.address = self._generate_address()
    
    def _generate_address(self) -> str:
        """生成钱包地址 (简化版)"""
        hash_obj = hashlib.sha256(f"{self.user_id}{self.currency}{datetime.now()}".encode())
        return hash_obj.hexdigest()[:34]
    
    @property
    def total_balance(self) -> float:
        """总余额"""
        return self.available_balance + self.frozen_balance


@dataclass
class Transaction:
    """交易记录"""
    tx_id: str
    user_id: str
    wallet_id: str
    currency: str
    tx_type: TransactionType
    amount: float
    fee: float = 0.0
    status: TransactionStatus = TransactionStatus.PENDING
    from_address: str = ""
    to_address: str = ""
    tx_hash: str = ""  # 区块链交易哈希
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tx_id is None:
            self.tx_id = str(uuid.uuid4())


@dataclass
class WithdrawalRequest:
    """提现申请"""
    request_id: str
    user_id: str
    wallet_id: str
    currency: str
    amount: float
    to_address: str
    fee: float
    status: TransactionStatus = TransactionStatus.PENDING
    approval_required: bool = False
    approved_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class WalletManager:
    """
    钱包管理器
    
    功能:
    - 多币种钱包管理
    - 充值/提现处理
    - 资金划转
    - 余额查询
    """
    
    def __init__(self):
        """初始化钱包管理器"""
        # 用户钱包 {user_id: {currency: Wallet}}
        self.user_wallets: Dict[str, Dict[str, Wallet]] = {}
        
        # 交易记录
        self.transactions: List[Transaction] = []
        
        # 提现申请
        self.withdrawal_requests: List[WithdrawalRequest] = []
        
        # 平台钱包
        self.platform_wallets: Dict[str, Wallet] = {}
        
        # 提现限额
        self.withdrawal_limits = {
            'BTC': {'daily': 10.0, 'single': 5.0},
            'ETH': {'daily': 100.0, 'single': 50.0},
            'USDT': {'daily': 100000.0, 'single': 50000.0}
        }
        
        # 提现手续费
        self.withdrawal_fees = {
            'BTC': 0.0005,
            'ETH': 0.005,
            'USDT': 1.0
        }
        
        logger.info("钱包管理器已初始化")
    
    def create_wallet(self, user_id: str, currency: str, wallet_type: WalletType = WalletType.HOT) -> Wallet:
        """
        创建钱包
        
        Args:
            user_id: 用户 ID
            currency: 币种
            wallet_type: 钱包类型
        
        Returns:
            Wallet 对象
        """
        # 检查钱包是否已存在
        if user_id in self.user_wallets and currency in self.user_wallets[user_id]:
            return self.user_wallets[user_id][currency]
        
        # 创建新钱包
        wallet = Wallet(
            wallet_id=None,
            user_id=user_id,
            currency=currency,
            wallet_type=wallet_type
        )
        
        # 保存钱包
        if user_id not in self.user_wallets:
            self.user_wallets[user_id] = {}
        self.user_wallets[user_id][currency] = wallet
        
        logger.info(f"为用户 {user_id} 创建 {currency} 钱包：{wallet.wallet_id}")
        
        return wallet
    
    def get_wallet(self, user_id: str, currency: str) -> Optional[Wallet]:
        """
        获取钱包
        
        Args:
            user_id: 用户 ID
            currency: 币种
        
        Returns:
            Wallet 对象
        """
        if user_id in self.user_wallets and currency in self.user_wallets[user_id]:
            return self.user_wallets[user_id][currency]
        return None
    
    def get_balance(self, user_id: str, currency: str) -> Dict:
        """
        获取余额
        
        Args:
            user_id: 用户 ID
            currency: 币种
        
        Returns:
            余额信息
        """
        wallet = self.get_wallet(user_id, currency)
        if not wallet:
            return {"error": "钱包不存在"}
        
        return {
            "user_id": user_id,
            "currency": currency,
            "total_balance": wallet.total_balance,
            "available_balance": wallet.available_balance,
            "frozen_balance": wallet.frozen_balance,
            "wallet_id": wallet.wallet_id,
            "address": wallet.address,
            "timestamp": datetime.now().isoformat()
        }
    
    def deposit(self, user_id: str, currency: str, amount: float, from_address: str = "", tx_hash: str = "") -> Tuple[bool, str]:
        """
        充值
        
        Args:
            user_id: 用户 ID
            currency: 币种
            amount: 金额
            from_address: 来源地址
            tx_hash: 区块链交易哈希
        
        Returns:
            (success, message)
        """
        if amount <= 0:
            return False, "充值金额必须大于 0"
        
        # 获取或创建钱包
        wallet = self.get_wallet(user_id, currency)
        if not wallet:
            wallet = self.create_wallet(user_id, currency)
        
        # 更新余额
        wallet.balance += amount
        wallet.available_balance += amount
        wallet.updated_at = datetime.now()
        
        # 创建交易记录
        tx = Transaction(
            tx_id=None,
            user_id=user_id,
            wallet_id=wallet.wallet_id,
            currency=currency,
            tx_type=TransactionType.DEPOSIT,
            amount=amount,
            from_address=from_address,
            tx_hash=tx_hash,
            status=TransactionStatus.COMPLETED,
            description=f"充值 {amount} {currency}",
            completed_at=datetime.now()
        )
        
        self.transactions.append(tx)
        
        logger.info(f"充值成功：{user_id} 充值 {amount} {currency}")
        
        return True, f"充值成功：{amount} {currency}"
    
    def withdraw(self, user_id: str, currency: str, amount: float, to_address: str) -> Tuple[bool, str]:
        """
        提现
        
        Args:
            user_id: 用户 ID
            currency: 币种
            amount: 金额
            to_address: 提现地址
        
        Returns:
            (success, message)
        """
        # 检查金额
        if amount <= 0:
            return False, "提现金额必须大于 0"
        
        # 获取钱包
        wallet = self.get_wallet(user_id, currency)
        if not wallet:
            return False, "钱包不存在"
        
        # 检查余额
        if amount > wallet.available_balance:
            return False, f"余额不足：可用 {wallet.available_balance} {currency}"
        
        # 计算手续费
        fee = self.withdrawal_fees.get(currency, 0.0)
        total_amount = amount + fee
        
        if total_amount > wallet.available_balance:
            return False, f"余额不足 (含手续费): 需要 {total_amount} {currency}"
        
        # 检查限额
        if currency in self.withdrawal_limits:
            limits = self.withdrawal_limits[currency]
            if amount > limits['single']:
                return False, f"超过单笔限额：{limits['single']} {currency}"
        
        # 检查是否需要审批
        approval_required = amount > limits.get('single', 0) * 0.5 if currency in self.withdrawal_limits else False
        
        # 冻结金额
        wallet.available_balance -= total_amount
        wallet.frozen_balance += total_amount
        wallet.updated_at = datetime.now()
        
        # 创建提现申请
        request = WithdrawalRequest(
            request_id=None,
            user_id=user_id,
            wallet_id=wallet.wallet_id,
            currency=currency,
            amount=amount,
            to_address=to_address,
            fee=fee,
            approval_required=approval_required
        )
        
        self.withdrawal_requests.append(request)
        
        # 创建交易记录
        tx = Transaction(
            tx_id=None,
            user_id=user_id,
            wallet_id=wallet.wallet_id,
            currency=currency,
            tx_type=TransactionType.WITHDRAWAL,
            amount=amount,
            fee=fee,
            to_address=to_address,
            status=TransactionStatus.PENDING if approval_required else TransactionStatus.PROCESSING,
            description=f"提现 {amount} {currency} 到 {to_address}"
        )
        
        self.transactions.append(tx)
        
        logger.info(f"提现申请：{user_id} 申请提现 {amount} {currency}")
        
        return True, f"提现申请已提交：{amount} {currency} (手续费：{fee})"
    
    def approve_withdrawal(self, request_id: str, approved_by: str) -> Tuple[bool, str]:
        """
        审批提现申请
        
        Args:
            request_id: 申请 ID
            approved_by: 审批人
        
        Returns:
            (success, message)
        """
        # 查找申请
        request = next((r for r in self.withdrawal_requests if r.request_id == request_id), None)
        if not request:
            return False, "提现申请不存在"
        
        if request.status != TransactionStatus.PENDING:
            return False, f"申请状态为 {request.status.value}，无法审批"
        
        # 更新申请状态
        request.status = TransactionStatus.PROCESSING
        request.approved_by = approved_by
        
        # 更新交易状态
        tx = next((t for t in self.transactions if t.tx_id == request.request_id), None)
        if tx:
            tx.status = TransactionStatus.PROCESSING
        
        logger.info(f"提现申请已批准：{request_id} by {approved_by}")
        
        return True, "提现申请已批准"
    
    def process_withdrawal(self, request_id: str, tx_hash: str) -> Tuple[bool, str]:
        """
        处理提现（打款）
        
        Args:
            request_id: 申请 ID
            tx_hash: 区块链交易哈希
        
        Returns:
            (success, message)
        """
        # 查找申请
        request = next((r for r in self.withdrawal_requests if r.request_id == request_id), None)
        if not request:
            return False, "提现申请不存在"
        
        if request.status != TransactionStatus.PROCESSING:
            return False, f"申请状态为 {request.status.value}，无法处理"
        
        # 获取钱包
        wallet = self.get_wallet(request.user_id, request.currency)
        if not wallet:
            return False, "钱包不存在"
        
        # 扣减余额
        total_amount = request.amount + request.fee
        wallet.balance -= total_amount
        wallet.frozen_balance -= total_amount
        wallet.updated_at = datetime.now()
        
        # 更新申请状态
        request.status = TransactionStatus.COMPLETED
        request.completed_at = datetime.now()
        
        # 更新交易状态
        tx = next((t for t in self.transactions if t.tx_id == request_id), None)
        if tx:
            tx.status = TransactionStatus.COMPLETED
            tx.tx_hash = tx_hash
            tx.completed_at = datetime.now()
        
        logger.info(f"提现已完成：{request_id} - {request.amount} {request.currency}")
        
        return True, "提现已完成"
    
    def transfer(self, from_user_id: str, to_user_id: str, currency: str, amount: float) -> Tuple[bool, str]:
        """
        用户间转账
        
        Args:
            from_user_id: 转出用户
            to_user_id: 转入用户
            currency: 币种
            amount: 金额
        
        Returns:
            (success, message)
        """
        if amount <= 0:
            return False, "转账金额必须大于 0"
        
        # 获取转出钱包
        from_wallet = self.get_wallet(from_user_id, currency)
        if not from_wallet:
            return False, "转出钱包不存在"
        
        # 检查余额
        if amount > from_wallet.available_balance:
            return False, f"余额不足：可用 {from_wallet.available_balance} {currency}"
        
        # 获取或创建转入钱包
        to_wallet = self.get_wallet(to_user_id, currency)
        if not to_wallet:
            to_wallet = self.create_wallet(to_user_id, currency)
        
        # 执行转账
        from_wallet.available_balance -= amount
        from_wallet.balance -= amount
        from_wallet.updated_at = datetime.now()
        
        to_wallet.available_balance += amount
        to_wallet.balance += amount
        to_wallet.updated_at = datetime.now()
        
        # 创建交易记录
        tx = Transaction(
            tx_id=None,
            user_id=from_user_id,
            wallet_id=from_wallet.wallet_id,
            currency=currency,
            tx_type=TransactionType.TRANSFER,
            amount=amount,
            to_address=to_wallet.address,
            status=TransactionStatus.COMPLETED,
            description=f"转账给 {to_user_id}",
            completed_at=datetime.now()
        )
        
        self.transactions.append(tx)
        
        logger.info(f"转账成功：{from_user_id} → {to_user_id} {amount} {currency}")
        
        return True, f"转账成功：{amount} {currency}"
    
    def freeze_balance(self, user_id: str, currency: str, amount: float, reason: str = "") -> Tuple[bool, str]:
        """
        冻结余额
        
        Args:
            user_id: 用户 ID
            currency: 币种
            amount: 金额
            reason: 原因
        
        Returns:
            (success, message)
        """
        wallet = self.get_wallet(user_id, currency)
        if not wallet:
            return False, "钱包不存在"
        
        if amount > wallet.available_balance:
            return False, f"可用余额不足：{wallet.available_balance} {currency}"
        
        wallet.available_balance -= amount
        wallet.frozen_balance += amount
        wallet.updated_at = datetime.now()
        
        logger.info(f"冻结余额：{user_id} {amount} {currency} - {reason}")
        
        return True, f"已冻结 {amount} {currency}"
    
    def unfreeze_balance(self, user_id: str, currency: str, amount: float) -> Tuple[bool, str]:
        """
        解冻余额
        
        Args:
            user_id: 用户 ID
            currency: 币种
            amount: 金额
        
        Returns:
            (success, message)
        """
        wallet = self.get_wallet(user_id, currency)
        if not wallet:
            return False, "钱包不存在"
        
        if amount > wallet.frozen_balance:
            return False, f"冻结余额不足：{wallet.frozen_balance} {currency}"
        
        wallet.frozen_balance -= amount
        wallet.available_balance += amount
        wallet.updated_at = datetime.now()
        
        logger.info(f"解冻余额：{user_id} {amount} {currency}")
        
        return True, f"已解冻 {amount} {currency}"
    
    def get_user_transactions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        获取用户交易记录
        
        Args:
            user_id: 用户 ID
            limit: 数量限制
        
        Returns:
            交易记录列表
        """
        user_txs = [tx for tx in self.transactions if tx.user_id == user_id]
        user_txs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [
            {
                "tx_id": tx.tx_id,
                "type": tx.tx_type.value,
                "currency": tx.currency,
                "amount": tx.amount,
                "fee": tx.fee,
                "status": tx.status.value,
                "created_at": tx.created_at.isoformat(),
                "description": tx.description
            }
            for tx in user_txs[:limit]
        ]
    
    def get_stats(self) -> Dict:
        """获取钱包统计"""
        total_users = len(self.user_wallets)
        total_wallets = sum(len(currencies) for currencies in self.user_wallets.values())
        total_transactions = len(self.transactions)
        pending_withdrawals = len([r for r in self.withdrawal_requests if r.status == TransactionStatus.PENDING])
        
        return {
            "total_users": total_users,
            "total_wallets": total_wallets,
            "total_transactions": total_transactions,
            "pending_withdrawals": pending_withdrawals,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """测试主函数"""
    print("=" * 60)
    print("💰 GlobalTokenHub - 钱包管理测试")
    print("=" * 60)
    
    # 创建钱包管理器
    manager = WalletManager()
    
    print("\n✅ 钱包管理器初始化完成")
    
    # 创建钱包
    print("\n📋 创建钱包...")
    wallet1 = manager.create_wallet("user_001", "BTC")
    wallet2 = manager.create_wallet("user_001", "USDT")
    wallet3 = manager.create_wallet("user_002", "BTC")
    
    print(f"  user_001 BTC 钱包：{wallet1.wallet_id[:16]}...")
    print(f"  user_001 USDT 钱包：{wallet2.wallet_id[:16]}...")
    print(f"  user_002 BTC 钱包：{wallet3.wallet_id[:16]}...")
    
    # 测试充值
    print("\n💵 测试充值...")
    success, msg = manager.deposit("user_001", "BTC", 1.0, "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    print(f"  BTC 充值：{'✅' if success else '❌'} - {msg}")
    
    success, msg = manager.deposit("user_001", "USDT", 100000.0)
    print(f"  USDT 充值：{'✅' if success else '❌'} - {msg}")
    
    # 查询余额
    print("\n💳 查询余额...")
    balance = manager.get_balance("user_001", "BTC")
    print(f"  user_001 BTC: {balance.get('available_balance', 0):,.4f}")
    
    balance = manager.get_balance("user_001", "USDT")
    print(f"  user_001 USDT: ${balance.get('available_balance', 0):,.2f}")
    
    # 测试提现
    print("\n💸 测试提现...")
    success, msg = manager.withdraw("user_001", "BTC", 0.1, "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")
    print(f"  BTC 提现：{'✅' if success else '❌'} - {msg}")
    
    # 测试转账
    print("\n💱 测试转账...")
    success, msg = manager.transfer("user_001", "user_002", "BTC", 0.05)
    print(f"  BTC 转账：{'✅' if success else '❌'} - {msg}")
    
    # 查询交易记录
    print("\n📜 交易记录...")
    txs = manager.get_user_transactions("user_001", limit=5)
    print(f"  user_001 最近交易：{len(txs)} 条")
    for tx in txs[:3]:
        print(f"    - {tx['type']}: {tx['amount']} {tx['currency']} ({tx['status']})")
    
    # 统计信息
    print("\n📊 钱包统计...")
    stats = manager.get_stats()
    print(f"  总用户数：{stats['total_users']}")
    print(f"  总钱包数：{stats['total_wallets']}")
    print(f"  总交易数：{stats['total_transactions']}")
    print(f"  待处理提现：{stats['pending_withdrawals']}")
    
    print("\n" + "=" * 60)
    print("✅ 钱包管理测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
