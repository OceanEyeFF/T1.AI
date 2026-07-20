---
title: "WT-R4-A1 Lake / Source Contract (draft)"
artifact_type: "lake-source-contract"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
deliverable: "A1-D1"
status: "frozen"
updated: "2026-07-20T21:22:00+08:00"
owner: "OceanEyeFF"
freeze_state: "frozen_for_A2"
---

# WT-R4-A1 — 湖 / 源合同草案

> **性质：** A1 文档交付物（T1）。供 A2 合同测 / A3 limited-live 消费。  
> **本文件不授权：** 灌湖、live 拉取、训练、Phase 4、EXEC-002。  
> **Init 锁定：** A1_Q3 = DataLake 唯一消费入口；池绑定 A0 `custom_research_liquidity_quality_v1@1`。

## 1. Control Signal

```yaml
contract_id: MS-R4-001-lake-source-v0
status: frozen_for_A2
primary_source: tushare
backup_source: akshare
consumer_entry: ashare_infra.lake.DataLake
universe_binding:
  stock_pool_id: custom_research_liquidity_quality_v1
  stock_pool_version: "1"
  symbols_count: 61
  registry_path: inputs/pools/research_liquidity_quality/
  is_research_only: true
history_start: "2023-01-01"
adjust_default: qfq
live_policy: L2_limited_live_only_after_explicit_approve  # A3; not A1
cache_root: inputs/data/cache
token_policy: env_TUSHARE_TOKEN_only_never_in_repo
rate_limits_ref: WT-R4-A1-rate-limit-recommendations.md
rate_limits_status: approved_accept_recommended
rate_limits_caps: {rpm: 180, daily_per_api: 80000}
rate_limits_promo: promote_to_inputs_configs_in_A2_or_A3
freeze_state: frozen_for_A2
frozen_at: "2026-07-20T21:22:00+08:00"
```

## 2. Purpose

为 MS-R4 固定一条**可复现、可审计**的日频数据湖合同：

1. 研究 / 脚本 / lab 消费方只经 `DataLake` 取数；
2. 默认源为 TuShare（D5）；AkShare 为备用语义，**不删除**实现；
3. 验收与补洞绑定 **A0 批准池版本**，不以 `low_manipulation` 为最终 universe；
4. 历史窗口自 `2023-01-01` 起（与池 `effective_start` 对齐）。

## 3. Source Roles

| Role | Source | When used | Notes |
|------|--------|-----------|--------|
| **Primary** | TuShare Pro | R4 默认日频湖；A3 L2 补洞 | `TUSHARE_TOKEN` 仅环境变量 |
| **Backup** | AkShare | TuShare 不可用 / 对比 / 非 R4 主路径 | 保留适配器；不得升格为 R4 默认 |
| **Smoke / CI** | `DataLake(default_source="smoke", loader=…)` | 无网测 | 见 `ashare_infra.lake.smoke` |
| **ODP** | OpenBB / yfinance | 非本里程碑主合同 | 不纳入 A1 冻结字段 |

`inputs/configs/data_source.toml` 当前 `default_source: akshare` 为仓库历史默认；**R4 湖工作以本文件为准**（TuShare primary）。A2 可提议配置对齐，但不在 A1 改生产配置（除非另批）。

## 4. Consumer Entry（强制）

| 允许 | 禁止 |
|------|------|
| `from ashare_infra.lake import DataLake` | 新业务代码 `from … import load_or_fetch_*` |
| `lake.load_daily_bars` / `load_scope_bars` / `load_index_daily` | 直调 `ashare_infra.data.*_source.load_or_fetch_*`（适配器内部除外） |
| `lake.load_stock_basic` / lifecycle meta（本地） | 把 token 写入 artifact / 仓内文件 |
| 既有 `ashare_lab.data` **shim** 过渡（不鼓励新写） | 把 `ashare_exec` 执行策略层当成数据湖合同的一部分 |

**引擎 / 执行策略边界：** `ashare_exec`（Decision → WeightMapper → Strategy）消费行情结果，**不**定义湖布局；本 WT 不扩展 EXEC。

约定测（已在 develop / Infra Phase 2）：`tests/contract/infra/test_no_direct_load_or_fetch.py`。A2 可增 R4 池绑定相关测。

## 5. Universe Binding

| Field | Value |
|-------|--------|
| `stock_pool_id` | `custom_research_liquidity_quality_v1` |
| `stock_pool_version` | `1` |
| `symbols_count` | 61 |
| `hard_cap` | 100（已满足） |
| `soft_target` | 80（**未满足**；缺口属 A3 扩池，非本文件失败条件） |
| `effective_start` | `2023-01-01` |
| `is_research_only` | `true` until MS-R4 milestone Gate |
| Contrast-only | `inputs/pools/low_manipulation/` — **不得**升格为最终 universe |

符号形式：池 CSV 为裸 6 位码；TuShare cache / API 使用 `ts_code`（如 `000001.SZ`）。`DataLake` / `ashare_lab.symbols` 负责规范化；A2 schema 测须覆盖裸码 ↔ ts_code。

## 6. Dataset Coverage（日频）

| Dataset | Cache namespace | Primary API surface | Required for A0 pool hygiene |
|---------|---------------|---------------------|------------------------------|
| OHLCV qfq | `tushare_qfq/{ts_code}/year=YYYY/part.parquet` | `DataLake.load_daily_bars(..., source="tushare", adjust="qfq")` | **yes** |
| Daily basic | `tushare_daily_basic/{ts_code}/…` | via tushare adapter / future lake helpers | **yes**（A0 已用） |
| Moneyflow | `tushare_moneyflow/{ts_code}/…` | via tushare adapter / future lake helpers | **yes**（A0 已用） |
| Index / ETF anchor | `tushare_qfq/510300.SH/…` | `load_index_daily` 或同布局 qfq | **deferred**（A1_Q2：空目录；A3 fill） |
| Meta stock_basic | `{cache}/meta/stock_basic.{csv,parquet}` | `DataLake.load_stock_basic` | optional for R4 A1；本地 only |

**Raw / hfq：** 适配器支持 `tushare` / `tushare_hfq` 等命名空间；**R4 默认合同锁定 qfq**。混用复权基址须显式声明，禁止静默拼接。

**Amount 单位：** TuShare `amount` = **千元**；策略侧亿元换算用 `/1e5`（A0 已审计）。合同消费者不得再假设 `/1e8`。

## 7. Cache Layout Contract

```text
inputs/data/cache/
  tushare_qfq/{ts_code}/year={YYYY}/part.parquet
  tushare_daily_basic/{ts_code}/year={YYYY}/part.parquet
  tushare_moneyflow/{ts_code}/year={YYYY}/part.parquet
  meta/stock_basic.csv|parquet          # optional local meta
  akshare/…                             # backup / non-primary (Infra Phase 2 layout)
```

- **Partition key：** `year=YYYY` + `part.parquet`（与 `ashare_infra.data.tushare_source` 一致）。
- **Idempotent read：** cache-first（D3=R1）；`refresh=True` 的合并语义以适配器为准（禁止制造永久空洞——Infra Phase 1.5 已修）。
- **Write authority：** 仅适配器 / 经批准的 A3 补洞路径；A1 **零写入**。

详细列级 schema 见后续 `WT-R4-A1-schema-draft.md`（T3）。Inventory 见 `WT-R4-A1-cache-inventory.md`（T2）。

## 8. Time & Reproducibility

| Rule | Value |
|------|--------|
| History start | `2023-01-01`（含） |
| Calendar | A-share 交易日；缺失 bar 策略由 `ashare_infra.guard` / 调用方声明 |
| `as_of` | `DataLake` / `truncate_as_of` 支持截断；研究不得偷看未来 |
| Reproducibility | 同一 `cache_dir` + 同一池版本 + `refresh=False` → 同结果（barring 本地 cache 变更） |

## 9. Live / Rate-Limit Policy（指针）

| Mode | Allowed in A1? | Notes |
|------|----------------|-------|
| Cache-only read | **yes** | Inventory / 合同验证 |
| Silent full-campaign / 全市场 | **no** | 里程碑禁止 |
| L2 limited-live | **no in A1** | 仅 A3 + 显式批准 + 日/RPM 上限 |
| Token in repo | **no** | 永久禁止 |

数值日调用 / RPM 见 `WT-R4-A1-rate-limit-recommendations.md`（T4 v1：**approved** `accept_recommended` → **180 RPM / 80000·API·日**；平台硬顶 200 / 100000。v0 300/50 已废止）。

## 10. Acceptance Binding（给后续 WT）

A2–A4 / 里程碑验收应断言：

1. 默认路径语义 = TuShare + qfq + 本布局；
2. 消费方经 `DataLake`（或经批准的测试 double）；
3. Universe = `custom_research_liquidity_quality_v1@1`（或后续**显式**升版池）；
4. 无 token 入仓；无未批准 live；
5. `510300.SH` 在填洞前可标记 `index_available=false`（不阻断 A1 草案）。

## 11. Explicit Non-Goals

- 本文件不实现加载器重构（A2）
- 不执行 limited-live 补洞（A3）
- 不做 derived / QA 终稿（A4）
- 不训练、不晋升模型
- 不合并 Phase 4 lab 去重、不扩展 `ashare_exec`
- 不把 soft_target 80 当成 A1 失败（已接受 residual → A3）

## 12. Related Artifacts

| Artifact | Role |
|----------|------|
| `.servo/worktrack/WT-R4-A1-contract.md` | Worktrack 范围 |
| `.servo/worktrack/WT-R4-A0-data-gaps.md` | A0 cache 基线 gaps |
| `.servo/worktrack/WT-R4-A0-closeout.md` | 池交付与 Gate |
| `docs/reference/data_contract.md` | 通用字段/分区（将被 T3 细化） |
| `docs/architecture/repo_structure_guide.md`（develop） | DataLake 取数约定 |
| `inputs/pools/research_liquidity_quality/` | 批准池三件套 |

## 13. Change Control

- **Draft → Frozen：** A1 Gate 通过；`freeze_state=frozen_for_A2`（2026-07-20 Close）。
- 冻结后改 primary/backup/布局/池绑定 → 须新 worktrack 或显式变更记录，不得静默改。
