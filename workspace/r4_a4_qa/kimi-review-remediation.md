# Kimi Code Review — 反馈与修复记录

- generated_at: 2026-07-28T16:55:00+08:00
- reviews:
  - `workspace/r4_a4_qa/kimi-codereview-WT-R4-A4-T4-T5.md`（T4/T5 专项）
  - `workspace/r4_a4_qa/kimi-codereview-MS-R4-001-full.md`（MS-R4 A0–A4 全量）
- code_base_tip: `60cbf22`（修复在 working tree，待 commit）

## 两份报告结论（反馈）

| 报告 | Verdict | 要点 |
|------|---------|------|
| T4/T5 | pass_with_residuals | 50 passed 可复现；P3：qa-summary 脱节、closeout 跟踪、AO-O1 扫描面有限 |
| MS-R4 全量 | pass_with_residuals | 118 passed；无 P0/P1；6×P2 + 若干 P3；不阻塞 Residual Confirmation |

## 已修复（本次 working tree）

| ID | 问题 | 修复 |
|----|------|------|
| **F-05** | 无 pending 时仍标 `completed`，忽略 `failed` job | `tushare_batch._sync_manifest_when_no_pending` |
| **F-06** | 非墙失败返回「成功形」`BatchRunResult` | `BatchRunResult.failed: bool`；失败路径 `failed=True` |
| **F-11** | manifest `save` 非原子 | tmp + `replace` |
| **F-03**（部分） | 损坏 parquet 导致 load 硬失败 | `_read_cached_partitions` 对 OSError/ValueError fail-open skip |
| **F-03**（部分） | cache 写非原子 | `_write_partitioned` tmp + `replace` |
| **T4-T5 P3** | `qa-summary.json` 陈旧 | 字段同步（见同目录 `qa-summary.json`） |

**测试：** `tests/unit/infra/test_tushare_batch.py` 新增 F-05/F-06 回归；batch 相关 **13 passed**。

## 未改代码（登记 / 后续）

| ID | 处置 | 说明 |
|----|------|------|
| F-01 | **residual（AO-O4）** | 6 文件 AST 扫描；全仓合同待 AO-O4 |
| F-02 | **residual + 纪律** | `build_sequence_dataset_market_state.py` 不得纳入 R4 live 管线 |
| F-04 | **follow-up WT** | cache-first interior hole 检测需产品决策 |
| F-07–F-13 | **文档 / 后续** | 硬编码 61、factory 软绑定、ETF dry-run 预算、F-12 部分 rebuild 等 |
| F-14 | **纪律** | `output/`、pool 多副本、derived 需本地 materialization |
| T4 P3 closeout | **提交时** | 将 `WT-R4-A4-closeout.md` 与 Gate 写回一并入库 |

## MS 终验建议（继承 Kimi）

- 仍可 **pass_with_residuals** 进入 Residual Confirmation。
- 确认时点名：F-01 范围、F-02 不执行、F-04/F-07+ 是否接受为 residual。
- F-05/F-06 已在代码修复；终验表可注明 **closed_in_remediation_2026-07-28**。
