# test_decision_seam.py — WT-EXEC-001 knife-2

## Purpose

Lock the shared **Decision → WeightMapper → DecisionStrategy** seam for both
mechanical momentum and an ML stub, including `BacktestEngine.run`.

## SUT

- `ashare_exec.decision` (`MomentumDecision`, `MLStubDecision`, `DecisionResult`)
- `ashare_exec.weight_mapper.WeightMapper`
- `ashare_exec.adapt.as_strategy` / `DecisionStrategy`
- `MomentumTopNStrategy` (must wrap the same seam)

## Cases

| Case | Intent |
|------|--------|
| momentum scores only | Decision emits scores/ranked, not weights |
| WeightMapper top-N | Sole equal-weight producer |
| MomentumTopN uses seam | `_adapter()` is Decision + Mapper |
| mechanical + stub same path | Both call `as_strategy` + `target_weights` |
| extras override | Extensible context beyond history |
| BacktestEngine ×2 | Mechanical and stub both complete a run |
| DecisionResult fields | No `weights` field |

## Invariants

- Final weights only from `WeightMapper.map_weights`
- Engine Protocol unchanged (`target_weights(today, history)`)
- Stub is fake scores only (no real ML)

## Out of scope

- Rebalance / cost coverage
- recommendation / stock_pool
- Live network `run_backtest`
