# Infra Phase 1–2 白盒测试索引

> 文档颗粒度：guide · 时间属性：current · 分支工作：`cursor/infra-phase12-whitebox`

配套文档约定：每个白盒测试文件旁有同名 `.md`（五字段：purpose / SUT / cases / invariants / out-of-scope）。

## 怎么跑

```bash
conda activate py311-private
export PYTHONPATH=src:.

# Phase 1–2 白盒合集（unit only）
pytest -q \
  tests/unit/infra \
  tests/unit/guard \
  tests/unit/sim \
  tests/unit/lab \
  tests/unit/recommendation/test_recommendation_validator.py

# 或走既有 Infra A 脚本（含 integration/contract）
bash scripts/run_tests_infra_a.sh
```

## 模块 → 测试 → 配套文档

### Lake / façade

| 模块 | 测试 | 配套文档 |
|------|------|----------|
| `ashare_infra.lake.DataLake` | `tests/unit/infra/test_datalake.py` | [test_datalake.md](../../tests/unit/infra/test_datalake.md) |
| maintain 增量 | `test_datalake_maintain.py` | [test_datalake_maintain.md](../../tests/unit/infra/test_datalake_maintain.md) |
| stock_basic meta (1.5) | `test_datalake_stock_basic.py` | [test_datalake_stock_basic.md](../../tests/unit/infra/test_datalake_stock_basic.md) |
| audit harden | `test_phase1_audit_fixes.py` | [test_phase1_audit_fixes.md](../../tests/unit/infra/test_phase1_audit_fixes.md) |
| SmokeHarness | `test_smoke_fetch.py` | [test_smoke_fetch.md](../../tests/unit/infra/test_smoke_fetch.md) |

### Guard

| 模块 | 测试 | 配套文档 |
|------|------|----------|
| FetchGate / DataScope | `tests/unit/guard/test_fetch_gate.py` | [test_fetch_gate.md](../../tests/unit/guard/test_fetch_gate.md) |
| listing helpers | `test_listing.py` | [test_listing.md](../../tests/unit/guard/test_listing.md) |
| temporal | `test_temporal.py` | [test_temporal.md](../../tests/unit/guard/test_temporal.md) |
| execution | `test_execution.py` | [test_execution.md](../../tests/unit/guard/test_execution.md) |
| metrics | `test_metrics.py` | [test_metrics.md](../../tests/unit/guard/test_metrics.md) |
| sanity | `test_sanity.py` | [test_sanity.md](../../tests/unit/guard/test_sanity.md) |
| Infra A scope/metrics/sim edges | `tests/unit/infra/test_infra_a_*.py` | 同目录 `.md` |

### Sim

| 模块 | 测试 | 配套文档 |
|------|------|----------|
| fill_model / broker edges | `tests/unit/sim/test_fill_model.py` | [test_fill_model.md](../../tests/unit/sim/test_fill_model.md) |
| paper broker | `test_paper_broker.py` | [test_paper_broker.md](../../tests/unit/sim/test_paper_broker.md) |
| replay | `test_replay.py` | [test_replay.md](../../tests/unit/sim/test_replay.md) |

### Phase 2 consumers

| 模块 | 测试 | 配套文档 |
|------|------|----------|
| `ashare_lab.symbols` | `tests/unit/lab/test_symbols.py` | [test_symbols.md](../../tests/unit/lab/test_symbols.md) |
| `DatasetBuilder` lake path | `test_dataset_builder_lake.py` | [test_dataset_builder_lake.md](../../tests/unit/lab/test_dataset_builder_lake.md) |
| validator adapters + IC | `tests/unit/recommendation/test_recommendation_validator.py` | [test_recommendation_validator.md](../../tests/unit/recommendation/test_recommendation_validator.md) |

## 本轮补强（相对 develop@e1981a4）

| 缺口 | 动作 |
|------|------|
| Validator DataLake / IC 切入口 | 扩展 `test_recommendation_validator.py` |
| DatasetBuilder lake 白盒 | **新建** `test_dataset_builder_lake.py` |
| `apply_listing_filter` | **新建** `test_listing.py` |
| sell limit-down / symbols BJ / DataLake 错误边 / period_return 边 | 扩展既有文件 |

## 刻意不在本轮白盒

- 黑盒 / 集成 / 契约（I*、C*、`test_no_direct_load_or_fetch`）— 下一阶段
- Live TuShare 网络 IT
- `calendar.py` skeleton、完整 neutralization
