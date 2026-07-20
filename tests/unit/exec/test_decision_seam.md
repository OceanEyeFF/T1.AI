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
| ML stub int keys | `600000` int score maps to `"600000"` history key |
| ML stub short numeric pad | `1` / `"1"` → `"000001"` (lake.meta parity) |
| ML stub ts_code strip | `"600000.SH"` → `"600000"` |
| ML stub integral-float keys | `600000.0` normalizes to `"600000"` |
| ML stub non-finite drop | NaN/Inf scores dropped (parity with momentum) |
| ML stub NaN override | Later NaN override removes prior finite score |
| extras override | Construction picks A; extras flip to B |
| WeightMapper top-N | Sole equal-weight producer |
| MomentumTopN uses seam | `_adapter` is Decision + Mapper (cached) |
| mechanical + stub same path | Both call `as_strategy` + `target_weights` |
| BacktestEngine ×2 | Mechanical and stub both complete a run |
| DecisionResult fields | No `weights` field |

## Invariants

- Final weights only from `WeightMapper.map_weights`
- Engine Protocol unchanged (`target_weights(today, history)`)
- Stub is fake scores only (no real ML)
- Stub keys normalized (int/integral-float/str + zfill(6) + ts_code strip) and scores finite

## Out of scope

- Rebalance / cost coverage
- recommendation / stock_pool
- Live network `run_backtest`
