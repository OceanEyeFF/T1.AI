# T1.AI 系统输入输出与可扩展架构规范（v1）

> 目的：回答“复杂系统如何可维护、可解释、可扩展，以及最终输出是什么”。

---

## 1. 架构决策结论

- **主架构采用分段式（Pipeline-first）**：数据接入 → 特征/检索 → 信号建模 → 组合决策 → 执行反馈。
- **局部采用端到端（Module-level E2E）**：例如新闻事件抽取、PDF语义检索、单模态时序预测。
- **禁止全链路黑盒端到端**：为保持可解释性、可回放、可审计与故障定位能力。

该决策与现有“分层解耦、统一协议、动态集成、风控闭环”方向一致。

---

## 2. 可维护性设计（Maintenance by Design）

## 2.1 四层解耦

1. **Data Layer**（数据层）
   - 各数据源 connector 统一输出标准事件结构。
2. **Feature Layer**（特征层）
   - 特征注册中心管理依赖、刷新周期、回填策略。
3. **Signal Layer**（信号层）
   - 模型输出统一为标准信号协议。
4. **Decision/Execution Layer**（决策执行层）
   - 组合优化、风控约束、执行调度、成交归因。

## 2.2 运维约束（必须执行）

- 每个模块都有 owner、SLO（延迟/可用性）、回滚开关。
- 任何新模型上线必须通过 Champion-Challenger 灰度。
- 任何新数据源上线必须支持历史回放（replay）。

---

## 3. 可解释性设计（Explainability by Contract）

每次生成交易信号，必须产出解释结构：

- `top_features`: Top-k 因子贡献
- `top_events`: Top-k 新闻/事件贡献
- `regime_state`: 当前状态机 + 概率
- `uncertainty`: 不确定度分数
- `drift_flags`: 特征/解释漂移标记

并要求：
- 漂移阈值触发自动降仓或冻结交易；
- 所有解释可回溯到具体数据切片（新闻ID、PDF页码、行情窗口）。

---

## 4. 多源输入统一协议

## 4.1 输入数据源（首期）

- 股票高阶数据：OHLCV、盘口统计、资金流、行业映射
- 期货/大宗能源：主力连续、期限结构、跨品种价差
- 新闻：结构化事件、情绪、实体关系、时效衰减
- PDF（财报/研报）：BM25 + 向量混合检索结果

## 4.2 统一输入事件 Schema（逻辑）

```json
{
  "source": "news|equity|futures|pdf",
  "event_time": "2026-01-15T09:35:00+08:00",
  "ingest_time": "2026-01-15T09:35:02+08:00",
  "symbols": ["600519.SH"],
  "payload": {...},
  "quality_score": 0.93,
  "version": "v1.2.0"
}
```

---

## 5. 最终输出定义（核心）

## 5.1 分析输出（Research Output）

针对每个标的/时间窗输出：

```json
{
  "symbol": "600519.SH",
  "horizon": "5d",
  "alpha_score": 0.37,
  "uncertainty": 0.22,
  "regime_prob": {"R0": 0.05, "R1": 0.20, "R2": 0.62, "R3": 0.13},
  "explain": {
    "features": [{"name": "apm", "contrib": 0.18}],
    "events": [{"id": "news_123", "contrib": 0.09}],
    "docs": [{"doc_id": "pdf_88", "page": 14, "contrib": 0.05}]
  },
  "data_flags": ["news_delay_ok", "no_leakage"]
}
```

## 5.2 决策输出（Trading Output）

若系统维护持仓，最终必须输出：

```json
{
  "portfolio_date": "2026-01-15",
  "target_positions": [{"symbol": "600519.SH", "target_weight": 0.035}],
  "orders": [{"symbol": "600519.SH", "side": "BUY", "qty": 1200, "urgency": "medium"}],
  "risk_checks": {
    "max_drawdown_guard": "pass",
    "industry_exposure": "pass",
    "turnover_limit": "pass"
  },
  "action": "rebalance",
  "reason": "alpha_up + regime_R2 + low_drift"
}
```

> 关键点：信号不是最终产品，**持仓与订单才是最终产品**。

---

## 6. 扩展新数据源的标准流程

1. 新建 connector（抓取+标准化+质检）。
2. 注册到数据目录（频率、延迟、覆盖范围、许可约束）。
3. 开发最小特征集（不超过 5 个核心特征）。
4. 通过 A/B 回测（成本后收益 + 稳定性 + 解释增益）。
5. 灰度上线（仅影响 challenger，不直接影响 champion）。

上线门槛（全部满足）：
- 成本后增益为正；
- 漂移风险可控；
- 解释可追溯；
- 运维负担可接受（计算成本、延迟、故障率）。

---

## 7. 试用体验（用户视角）

用户每天应看到：

1. 当日推荐/调仓清单（可执行）。
2. 每条推荐的三行理由（因子、事件、文档证据）。
3. 风险提示（为何降仓/为何不交易）。
4. 与昨日相比的变化原因（regime 变化/信号漂移）。

如果用户看不到以上 4 项，则视为“不可用”。

---

## 8. 与现有文档的关系

- 架构原则继承：`docs/overview/future_state_blueprint.md`
- 对标依据：`docs/overview/ai_finance_external_benchmark_2026.md`
- 项目排期：`docs/overview/project_update_plan_2026Q1.md`

本规范是三者之间的“执行接口层文档”。
