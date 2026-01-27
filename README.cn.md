# TerraZip ⚡  
**AI-Native Unified Payment & Collection Framework**

TerraZip 是一个 **面向 AI Agent 与开发者的聚合收款与支付框架，意在解决人工智能时代机器与机器直接协同工作所需的付款问题，提升智能体之间交互的效率**。  
它通过统一抽象不同收款平台的能力，降低支付集成复杂度，并进一步将「支付」提升为 **可被 AI 驱动、可编排、可验证的基础能力**。


[English Version](README.md)

---

## 文档路径
- [快速开始](docs/quick_start.cn.md)
- [x402 示例](docs/x402.cn.md)
- [AI Agent 示例](docs/agent_doc.cn.md)

---

## ✨ 核心特性

### 1️⃣ 聚合收款（Unified Payments）
TerraZip 聚合了市面上主流的支付平台 API，  
**抹平不同平台在接口、流程、命名与验证方式上的差异**，为开发者提供一致、可扩展的收款与支付能力。

- 统一的收款 / 支付抽象
- 统一的订单与支付状态模型
- 可插拔的 Adapter 设计，便于扩展新平台

---

### 2️⃣ AI 驱动的支付框架（AI-Driven Payments）
在聚合收款之上，TerraZip 引入 **AI-Native 的支付设计**，使支付不再只是一次 RPC 调用，而是可被 Agent 理解、决策和执行的能力。

- 面向 AI Agent 的支付 / 收款状态机
- 支付意图（Payment Intent）与权限边界建模
- 支持「询价 → 确认 → 授权 → 支付」的 AI 交互流程
- 可作为 Agent Framework 的支付模块

---

### 3️⃣ Mock x402 实现（x402 Playground）
TerraZip 内置 **Mock x402 的完整实现与 Demo**，用于学习、测试与快速验证 AI 支付流程：

- x402 收款与支付流程
- Permit / Signature 校验
- Payment Intent & Allowance 验证
- 可直接运行的示例项目

> 适合：理解 x402、测试 AI Agent 的支付行为、快速原型开发

---

## 🚀 使用场景

- AI Agent 自动完成付费 API / 服务调用
- 多支付平台统一接入（Web2 / Web3）
- AI 驱动的自动订阅、计费与结算
- Payment-as-a-Tool 的 Agent 系统

---

## 🧭 项目愿景 & Roadmap

### 短期目标
- 聚合 **10+ 主流收款 / 支付平台**
- 稳定统一的 Payment Adapter 接口
- 完善 x402 / Permit / Allowance 验证流程

### 中期目标
- 构建 **标准化的 AI 支付工具（AI Payment Tools）**
- 支持 Agent 对支付的「可解释决策」
- 支持多 Agent / 多角色的支付协作模型

### 长期目标
- 打造 **AI-Native 的支付协议层**
- 让「支付」成为 AI Agent 的一等公民能力
- 推动 AI 与支付基础设施的标准化

---

## 🤝 Contributing
欢迎 PR、Issue 与讨论。  
如果你对 **AI Agent、支付系统、x402、Web3 / Web2 支付抽象**感兴趣，TerraZip 非常期待你的加入。

---

## 📜 License
Apache License 2.0
