---
title: "WT-EXEC-001 Brief — Stand up ashare_exec (Phase 3 / Infra B)"
artifact_type: "worktrack-brief"
worktrack_id: "WT-EXEC-001"
phase: "Phase 3"
track: "Infra B / execution strategy"
updated: "2026-07-20T14:45:00+08:00"
owner: "OceanEyeFF"
status: "b0_gate_ready"
prerequisite: "WT-INFRA-001 + 001.5 + 002 complete (DataLake/guard consumer cutover)"
suggested_branch: "cursor/exec-001-ashare-exec"
approval:
  scope_locked: true
  locked_decisions:
    - "new package ashare_exec (not inside ashare_infra)"
    - "Decision outputs scores/ranked candidates only"
    - "weights only via shared WeightMapper → Strategy.target_weights"
    - "Engine still only accepts ashare_infra.sim.engine.Strategy"
    - "Decision context is extensible (beyond history)"
    - "old ashare_lab.strategy/ + strategies/ deleted after reference; no long-lived lab shim"
    - "two cuts: B0 stand-up, then knife-2 DecisionAPI seam"
---

# WT-EXEC-001 — 立 `ashare_exec` 执行策略包

> 主对话入口 brief。Phase 1 / 1.5 / 2（`ashare_infra` 湖·guard·sim + 消费方切轨）已完成后的 **Phase 3 Infra B**。  
> **不要**塞进 MS-R4 worktrack；与 R4 池合同正交。  
> 开干建议：从 `develop` 拉 `cursor/exec-001-ashare-exec`，先做 **B0**，过 Gate 后再开刀 2。

## Why this package

原仓库主叙事是「模型预测准不准」→ `ashare_lab`（研究）+ `ashare_infra`（平台）。  
现在需要清晰的「信号 / 排名 → 目标权重 → BacktestEngine」执行层；该职责 **不属于** DataLake/guard，故 **新建 `ashare_exec`**，不并入 `ashare_infra`。

## Package map (target)

| 包 | 职责 |
|----|------|
| `ashare_lab` | 研究：features / labels / models / training / recommendation / stock_pool |
| `ashare_infra` | 平台：DataLake / guard / sim（含 `BacktestEngine` + `Strategy` Protocol） |
| **`ashare_exec`** | 执行策略：Decision（score/rank）→ `WeightMapper` → 满足 `Strategy.target_weights` |

引擎契约（已存在，本 WT **不改语义**）：

```python
# ashare_infra.sim.engine.Strategy
def target_weights(today, history: dict[str, DataFrame]) -> dict[str, float]: ...
```

## Locked interface decisions

| 项 | 决议 |
|----|------|
| Decision 输出 | **scores / ranked candidates** |
| 权重 | **仅**经共用 `WeightMapper` → 满足 `Strategy.target_weights` |
| Engine | 仍只认 `ashare_infra.sim.engine.Strategy` |
| Decision 上下文 | **可扩展**（可超 `history`：模型句柄、特征表、`as_of` 等） |
| 旧 `ashare_lab.strategy/` + `strategies/` | **参考后删除**；**不**保证同名兼容；**不**做长期 lab shim；配 **新** 测与模块文档 |

参考源（迁前可读，迁后删）：

- `src/ashare_lab/strategy/signal.py` — `SignalGenerator` / `MomentumSignalGenerator`（~137 LOC）
- `src/ashare_lab/strategy/portfolio.py` — `PortfolioManager`（~106 LOC；换仓/成本 TODO **本 WT 不实现**）
- `src/ashare_lab/strategies/momentum.py` — `MomentumTopNStrategy`（~38 LOC；当前 `run_backtest` live 路径）

调用面（须改引用）：

- `scripts/run_backtest.py` → 现 `ashare_lab.strategies.momentum`
- `tests/contract/reports/test_evaluation.py` → 同上
- 旧 unit：`tests/unit/backtest/test_strategy_*.py` → 替换为 `ashare_exec` 新测（可删旧文件）

## Two cuts (acceptance)

### B0 — 立包（先做）

**目标：** `ashare_exec` 可安装引用；至少一条机械策略能驱动 `run_backtest`。

| 要求 | 说明 |
|------|------|
| 新建 `src/ashare_exec/` | 包骨架 + 至少一个实现 `Strategy.target_weights` 的机械策略（可参考旧 `MomentumTopNStrategy`） |
| `scripts/run_backtest.py` | 改引用到 `ashare_exec`；跑通 |
| 旧 lab 路径 | **改引用或删除**；**无长期 shim** |
| DecisionAPI | **可不**完整落地（允许单体直接实现 `Strategy`，或内嵌临时 mapper） |
| 零范围 | 换仓/成本 TODO；recommendation；stock_pool；真实 ML |

**B0 Gate（建议）**

- [x] `from ashare_exec ...` 可用
- [x] `PYTHONPATH=src:.` 下 `run_backtest` 对夹具/缓存路径可完成一次回测（或等价单测驱动 `BacktestEngine.run`）
- [x] 仓库内无对已删 `ashare_lab.strategy` / `strategies` 的残留 import（除 changelog/brief）
- [x] 相关新测绿；fast/infra 无回归

> B0 实现落地于分支 `cursor/exec-001-ashare-exec`；Gate 证据：`tests/unit/exec/test_momentum.py` + `tests/contract/exec/test_no_lab_strategy_imports.py`。

建议目录（B0 可简化，刀 2 再扩）：

```text
src/ashare_exec/
  __init__.py
  strategies/
    momentum.py          # B0: mechanical Strategy (target_weights)
  # knife-2:
  # decision.py          # SimpleDecisionAPI → scores/rank
  # weight_mapper.py     # WeightMapper
  # adapt.py             # Decision + Mapper → Strategy
```

### 刀 2 — 扩展缝（B0 Gate 后）

**目标：** 固定「Decision → Mapper → Strategy」缝，机械与 ML stub 共用。

| 要求 | 说明 |
|------|------|
| `SimpleDecisionAPI` | 输出 score / ranked candidates；上下文可扩展 |
| `WeightMapper` | 唯一权重产生点；Decision **不得**直接出最终权重绕过 Mapper |
| Strategy 适配 | Decision + Mapper 适配为 `ashare_infra.sim.engine.Strategy` |
| 证明同缝 | ≥1 机械实现 + ≥1 ML **stub**（假分数即可） |
| 清理 | 删尽 lab 旧 strategy 残留；新配套测 + **短**模块文档（如 `docs/architecture/` 或 `docs/guides/` 一页） |

**刀 2 Gate（建议）**

- [ ] 机械与 stub 均经同一 Mapper/适配路径跑通 `BacktestEngine`（或单测等价）
- [ ] 无 Decision 直接写最终权重的旁路（除非日后显式开例外）
- [ ] 文档写清：`ashare_exec` vs `ashare_infra` vs `ashare_lab`；执行策略 ≠ `stock_pool` 选股策略

## Non-goals（本 WT 全程）

- 长期 `ashare_lab.strategy` / `strategies` 双 shim
- 实现 `PortfolioManager` 换仓门槛 / 成本覆盖 TODO
- 接入 `recommendation` / 动 `stock_pool` / MS-R4 池合同
- 修改 `BacktestEngine` 语义或 `Strategy` Protocol 形状（除非为扩展上下文另开审批）
- Decision 直接产出最终权重绕过 `WeightMapper`
- 本阶段真实 ML 训练 / 推理产品化（stub 形状即可）
- Phase 4 lab 去重全仓（sequence_builder 双份等）——另开

## Relation to prior phases

| 已完成 | 本 WT |
|--------|--------|
| Phase 1 `ashare_infra` | 复用 `sim.engine.Strategy` / `BacktestEngine` |
| Phase 1.5 meta | 不依赖 |
| Phase 2 DataLake 消费方切轨 | `run_backtest` 已走 DataLake；本 WT 只改 **strategy import** |
| MS-R4 | 并行、不抢道；选股策略留在 `stock_pool` |

## Suggested task order

| Seq | Cut | Task |
|-----|-----|------|
| T0 | B0 | 建 `ashare_exec` 包骨架 + py 包发现（若需改 `pyproject`/`setup`） |
| T1 | B0 | 迁/重写机械 `MomentumTopN`（或等价）实现 `Strategy` |
| T2 | B0 | 改 `run_backtest` + 删/改 lab 旧引用；新单测 |
| T3 | B0 | GATE B0 |
| T4 | 刀2 | `WeightMapper` + `SimpleDecisionAPI` + Strategy 适配 |
| T5 | 刀2 | 机械走缝 + ML stub；删残留；短文档 |
| T6 | 刀2 | GATE 刀2 |

## Main-chat starter

主对话可直接说：

> 按 `.servo/worktrack/WT-EXEC-001-brief.md` 开 **B0**：新建 `ashare_exec`，机械策略跑通 `run_backtest`，删除 lab 旧 `strategy`/`strategies`（无长期 shim）。

刀 2 须等 B0 Gate 后再开。
