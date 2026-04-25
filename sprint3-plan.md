# 🔥 ComputeHub Sprint 3 - 区块链结算层开发计划

> **目标**: 实现 Token 化计费和智能合约
> **预计耗时**: 10-14 天
> **开始时间**: 2026-04-25

---

## 📊 当前状态盘点

### ✅ 已完成
- 基础区块链结构 (genesis block, chain persistence)
- 结算计算 (GPU/CPU/storage 定价)
- 钱包管理 (create/credit/debit)
- 交易 mempool + 挖矿
- 基础争议处理

### 🔴 缺失 (Sprint 3 任务)

#### [3.1] Token 经济模型 (2-3天)
- [ ] CHB Token 完整定义 (ERC-20 风格接口)
- [ ] 充值接口 (deposit)
- [ ] 提现接口 (withdraw)
- [ ] 余额查询增强
- [ ] 交易记录查询

#### [3.2] 智能合约 (4-5天)
- [ ] TaskRegistry - 任务登记和状态追踪
- [ ] PaymentEscrow - 资金托管和释放
- [ ] NodeStaking - 节点质押和奖励
- [ ] DisputeResolution - 争议仲裁

#### [3.3] 物理计费引擎 (2-3天)
- [ ] 基于真实 GPU 利用率计费 (非简单时长)
- [ ] 按 token/按推理次数计费
- [ ] 用量统计和账单生成
- [ ] 自动结算触发

#### [3.4] Web3 集成 (1-2天)
- [ ] 钱包接口抽象
- [ ] 交易状态监控
- [ ] Gas 费优化

#### [3.5] 端到端测试 (2-3天)
- [ ] 完整计费测试
- [ ] 合约交互测试
- [ ] 争议处理流程测试

---

## 🎯 执行策略

1. **Phase 1**: 修复现有 bug + Token 经济模型
2. **Phase 2**: 智能合约四大模块
3. **Phase 3**: 物理计费引擎
4. **Phase 4**: Web3 集成 + 端到端测试

---

## 📁 文件变更计划

```
src/blockchain/
├── token.go           [NEW] Token 经济模型
├── escrow.go          [NEW] 资金托管合约
├── staking.go         [NEW] 节点质押合约
├── dispute.go         [NEW] 争议仲裁合约
├── billing.go         [NEW] 物理计费引擎
├── web3.go            [NEW] Web3 集成抽象
└── blockchain.go      [MOD] 修复 bug, 增强功能
```

---

*生成时间: 2026-04-25 01:10*
