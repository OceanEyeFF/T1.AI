# Independent Code Review — WT-R4-A4 T4+T5

- reviewer: kimi (independent, read-only, defect-first)
- reviewed_at: 2026-07-28
- range: `git diff c39f0d9..HEAD`（15c078d T4 + 60cbf22 T5 packet）+ uncommitted working-tree diff（Gate/Residuals/Close writeback）
- scope: T4 代码（test_no_direct_load_or_fetch.py, test_dataset_builder.py, data_source.toml）；T5 文档（WT-R4-A4-*.md, qa-summary.json）

## Verification Performed

- `git diff c39f0d9..HEAD` / `git diff HEAD` 全量审阅。
- pytest 实跑（非引用报告数字）：
  - `tests/integration/dataset/test_dataset_builder.py` + `tests/contract/infra/test_no_direct_load_or_fetch.py` + `tests/unit/lab/test_dataset_builder_lake.py` → **23 passed**（1.10s）
  - qa-report 列出的 7 个 derived 测试文件 → **27 passed**（0.75s）
  - 合计 **50 passed**，与 qa-report / qa-summary.json 的 `tests_focused_passed: 50` 一致。
- 代码声明交叉核对：
  - `DatasetConfig.source` 默认 `"tushare"` — `src/ashare_lab/dataset/builder.py:43` ✓
  - monkeypatch 目标签名与 `DataLake.load_daily_bars` 一致 — `src/ashare_infra/lake/__init__.py:121-130` ✓
  - `symbol_to_ts_code` / `symbol_to_odp_equity_symbol` 存在 — `src/ashare_lab/symbols.py:6,27` ✓
  - `make_r4_datalake` 默认 `refresh=False`、`R4_CACHE_ROOT=inputs/data/cache` — `r4_contract.py:39,155-166` ✓（toml 注释声明属实）
- 数据面抽查：`symbols.csv` 61 行（+header）、`601989` 在 registry、snapshot soft_target=80/hard_cap=100、`derived/{momentum,technical}` 各 61 symbol 目录、year=2023..2026 分区存在 ✓
- 直 import 面：`src/` 内 `load_or_fetch_*` 仅存在于 `ashare_infra.data`（定义/内部）与 `ashare_infra.lake`（façade）；`scripts/` 内仅 deferred 目标 `build_sequence_dataset_market_state.py` 直 import ✓

## Findings

### [P3] qa-summary.json 与未提交的 Gate 写回状态脱节 — workspace/r4_a4_qa/qa-summary.json:6
未提交 diff 把 qa-report / gate-evidence / residuals-round / consistency-matrix 的 tip 全部更新为 `60cbf22`、gate_status 更新为 `accepted`（2026-07-28），但同为 T5 deliverable 的 `qa-summary.json` 仍停留在 `tip: 15c078d`、`generated_at: 2026-07-24`，且无 `gate_status` 字段。机器可读摘要与 MD 姊妹件互相矛盾；Gate 写回 commit 时应同步再生成 JSON，否则下游消费 JSON 的工具会读到过期 tip/状态。

### [P3] gate-evidence 引用未跟踪文件 closeout.md — .servo/worktrack/WT-R4-A4-gate-evidence.md:60
Refs 表新增 `Closeout → .servo/worktrack/WT-R4-A4-closeout.md`，但该文件当前为 untracked（`git status` `??`）。若写回 commit 漏掉它，引用悬空。同理 `workspace/r4_a4_qa/kimi-codereview-run.log` 也未跟踪（噪声文件，建议不入库或加 ignore）。属提交纪律问题，非内容错误。

### [P3] 合同测试覆盖为 6 个硬编码文件，AO-O1 收窄当前无实际拦截面 — tests/contract/infra/test_no_direct_load_or_fetch.py:17-24
`SCAN_TARGETS` 是固定 6 文件列表；这 6 个文件目前均不 import `load_or_fetch_*`（无论 from lake 还是 data），故 `ALLOWED_PREFIXES` 去掉 `ashare_infra.data` 对现有扫描集行为无变化——收窄是纯语义收紧，真正的回归防护依赖"新业务文件不会被加进列表"。该洞为预存设计、且 AO-O4（全树 AST）已显式 deferred 并列入 accepted residuals，故仅记 P3 提示：allowlist 收窄的防护力在 AO-O4 落地前是声明性的。

## Non-Findings（核查后排除）

- consistency-matrix 的 "Evidence re-verify (2026-07-24) @ tip 60cbf22"：60cbf22 提交时间确为 2026-07-24 17:06，日期一致，非缺陷。
- t5-notes.md frontmatter `tip: 15c078d`：作者写于 60cbf22 提交前，pre-commit tip 属合理惯例。
- HEAD（60cbf22）committed 状态 `gate_status: not_accepted` 与工作树 `accepted` 的差异：gate-evidence 已自述 "Gate/Close writeback commit pending"，流程自洽。
- 工作树新增 `output/` untracked 目录：非本 WT 范围产物，不计 finding（建议确认是否需要 ignore）。

## Test Evidence（本评审实跑）

```text
pytest tests/integration/dataset/test_dataset_builder.py \
       tests/contract/infra/test_no_direct_load_or_fetch.py \
       tests/unit/lab/test_dataset_builder_lake.py -q
→ 23 passed in 1.10s

pytest tests/unit/infra/test_r4_derived_schema.py \
       tests/contract/infra/test_r4_derived_schema_contract.py \
       tests/unit/lab/test_r4_derived_builder.py \
       tests/integration/lab/test_r4_derived_builder_integration.py \
       tests/unit/infra/test_r4_derived_load.py \
       tests/contract/infra/test_r4_derived_load_contract.py \
       tests/integration/infra/test_r4_derived_load_integration.py -q
→ 27 passed in 0.75s
```

## Executive Summary

- T4 三文件改动正确、最小、注释与代码事实一致；实跑 23 passed。
- AO-O1 收窄正确但当前无实际拦截面（扫描集 6 文件均干净），防护力待 AO-O4。
- AO-O2 测试改写与 `DataLake.load_daily_bars` 真实签名、符号转换行为全部吻合。
- T5 文档数字可复现：focused suite 50 passed、pool 61/60、derived 61/61 均抽查属实。
- Findings 均为 P3：qa-summary.json 状态脱节、closeout.md 未跟踪引用、扫描覆盖声明性。
- 无 P0–P2；不阻塞已接受的 `pass_with_residuals` Gate。
- **verdict: pass_with_residuals**
