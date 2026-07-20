# test_momentum.py — Phase 3 / WT-EXEC-001 B0

## Purpose

Lock the `ashare_exec` mechanical momentum strategy and prove it can drive
`ashare_infra.sim.engine.BacktestEngine` without network I/O.

## SUT

- `ashare_exec.strategies.momentum.MomentumTopNStrategy`
- Package export `ashare_exec.MomentumTopNStrategy`
- `ashare_infra.sim.engine.BacktestEngine.run` (consumer of `Strategy`)

## Cases

| Case | Intent |
|------|--------|
| `test_import_ashare_exec_package` | Package discoverable / re-export |
| `test_momentum_top_n_filters_and_equal_weights` | Missing close / short history excluded; equal weight |
| `test_momentum_ranks_higher_return_first` | Top-1 picks higher lookback return |
| `test_backtest_engine_runs_with_momentum_strategy` | B0 gate: engine completes with synthetic bars |

## Invariants

- `target_weights` returns `{}` or weights summing to ~1.0
- No import of deleted `ashare_lab.strategy` / `ashare_lab.strategies`
- Does not implement DecisionAPI / WeightMapper (knife-2)

## Out of scope

- Rebalance threshold / cost coverage
- Live `scripts/run_backtest.py` network path
- ML decision stubs
