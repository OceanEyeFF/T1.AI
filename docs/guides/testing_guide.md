# 测试体系指南（MS-T1-001 / Arch-v1）

> 文档颗粒度：guide · 时间属性：current

## 布局

```text
tests/
  conftest.py                 # path-based markers + shared fixtures
  support/                    # paths / factories
  unit/                       # 纯逻辑 / 快
  integration/                # 多模块、tmp 文件系统
  contract/                   # 仓库文件 / CLI / 报告契约
```

Markers（由路径自动打标，另有 `slow` / `gpu`）：

| marker | 含义 |
|--------|------|
| `unit` | `tests/unit/` |
| `integration` | `tests/integration/` |
| `contract` | `tests/contract/` |
| `slow` | 较长训练环 |
| `gpu` | CUDA 路径 |

## 怎么跑

```bash
# 推荐环境
conda activate py311-private
export PYTHONPATH=src:.

# Fast（PR / 日常）：unit + contract
bash scripts/run_tests_fast.sh
# 或：bash scripts/run_develop_min_regression.sh

# Infra A（lake + sim + guard，无网络，夹具见 tests/fixtures/infra_a/）
bash scripts/run_tests_infra_a.sh
# 覆盖：tests/unit/{guard,infra,sim,backtest} + tests/integration/infra
#       + tests/integration/sources + tests/contract/infra + universe 集成

# Infra Smoke（模拟下载 / 加票 / 改起始日，无网络）
python scripts/run_infra_smoke.py
python scripts/run_infra_smoke.py --json

# Full
bash scripts/run_tests_full.sh

# Full + coverage（强制 fail_under，见 pyproject）
bash scripts/run_tests_cov.sh
```

### Infra A 清单（WT-INFRA-001-TQA）

白盒 Guard/Lake/Sim + 跨层 I* + 入口 C/Smoke。详见
`.servo/worktrack/WT-INFRA-001-tqa-gap-report.md`。

| ID | 状态 |
|----|------|
| U-G1..G5, U-S2, I1..I3, C1, Smoke | ✅ 基线 |
| U-G6 sanity / U-G7 temporal+as_of / U-G8 execution | ✅ |
| U-L2 maintain 增量 / U-S1 no-peek / I4 stockpool / I5 sanity / C2..C4 | ✅ |
| U-L3 stock_basic→DataLake | ✅ WT-INFRA-001.5（本地 meta；无网） |
| Phase 2 no-direct-`load_or_fetch` | ✅ `tests/contract/infra/test_no_direct_load_or_fetch.py` |

Coverage `source` 已含 `src/ashare_infra`（`pyproject.toml`）。

等价 marker 选择：

```bash
pytest -q -m "unit or contract"          # fast
pytest -q                                # full
pytest -q --cov=ashare_lab               # cov（读 pyproject fail_under）
```

## 覆盖率策略（Acc-balanced）

- 结构与分层是主交付；cov 是防回退锚，不是唯一 KPI。
- Fast **不**强制 cov。
- Full/cov job 使用 `fail_under`（当前 **76**，来自 A4 实测 TOTAL **78%** → `max(70, 78-2)`）。
- 禁止为冲覆盖率注水测例。

## 相关

- Milestone：`.servo/milestone/MS-T1-001.md`
- Inventory：`.servo/worktrack/WT-T1-A1-inventory.md`
- R4 延后交接：`.servo/worktrack/WT-T1-A4-r4-handoff.md`
