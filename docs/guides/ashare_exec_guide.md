# `ashare_exec` — 执行策略层（WT-EXEC-001）

> Phase 3 Infra B。引擎契约不变；本包只负责「分数/排名 → 目标权重」。

## 三包分工

| 包 | 职责 | 不要混淆 |
|----|------|----------|
| `ashare_infra` | DataLake / guard / sim（含 `BacktestEngine` + `Strategy` Protocol） | 不做选股池、不做研究训练 |
| **`ashare_exec`** | Decision（score/rank）→ **唯一** `WeightMapper` → 适配为 `Strategy` | **≠** `ashare_lab.stock_pool` 选股策略 |
| `ashare_lab` | 研究：features / models / recommendation / stock_pool | 旧 `strategy/` / `strategies/` 已删除，无 shim |

## 固定缝（刀 2）

```text
DecisionAPI.decide(ctx) → DecisionResult{scores, ranked}
        ↓
WeightMapper.map_weights(ranked) → {symbol: weight}
        ↓
DecisionStrategy.target_weights(today, history)  # 满足 Engine Strategy
```

- **Decision** 只出分数与排序；上下文用 `DecisionContext.extras` 扩展（模型句柄、特征表、`as_of` 等）。
- **权重只经 `WeightMapper`**；禁止 Decision 直接写最终权重绕过 Mapper。
- **机械与 ML stub 同缝**：`MomentumDecision` + `MLStubDecision` 均经 `as_strategy(...)`。

便捷封装：`MomentumTopNStrategy` 内部同样走该缝（兼容 `scripts/run_backtest.py`）。

## 最小用法

```python
from ashare_exec import (
    MLStubDecision,
    MomentumDecision,
    WeightMapper,
    as_strategy,
)
from ashare_infra.sim import BacktestConfig, BacktestEngine

mapper = WeightMapper(top_n=3)
mech = as_strategy(MomentumDecision(lookback=20, min_history=60), mapper)
stub = as_strategy(MLStubDecision(model_scores={"600000": 0.8, "000001": 0.2}), mapper)

engine = BacktestEngine(BacktestConfig())
# engine.run(data_by_symbol, strategy=mech)  # or stub
```

## Non-goals（本 WT）

换仓门槛 / 成本覆盖、recommendation 接入、改 Engine Protocol、真实 ML 产品化。
