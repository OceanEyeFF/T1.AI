---
title: "WT-R4-A3 T4 Notes — Soft80 Accepted Residual"
artifact_type: "worktrack-task-notes"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A3"
task_id: "R4-A3-T4"
updated: "2026-07-23T13:05:00+08:00"
owner: "OceanEyeFF"
status: "completed"
live_pull: "none"
---

# WT-R4-A3 T4 Notes

## Decisions locked (programmer 2026-07-23)

| ID | Choice |
|----|--------|
| D1 T4出口 | **C** 接受 soft80 残差 |
| D2 批次 | **零 live**（不为凑 80 再拉） |
| D3 API | N/A |
| D4 版本 | 池保持 **v1@1 / 61**（不重选） |
| D5 601989 | 保留在 v1@1；**试验子集默认排除** |
| D6 510300 | 接受 basic/mf 残差（**index 仅 qfq**） |
| D7 AO-O | T4 defer → **A4** |

Rationale: 试验阶段 61 只足够；正式接受 soft80 残差；不重选、不扩 cache，避免模糊中间态。

## Deliverables

| Item | Path / signal |
|------|----------------|
| Soft80 status constant | `R4_SOFT80_STATUS=accepted_residual` in `r4_contract.py` |
| Trial exclude | `R4_TRIAL_EXCLUDE_SYMBOLS` + `filter_r4_trial_symbols` |
| Index policy | `R4_INDEX_REQUIRED_NAMESPACES={tushare_qfq}` |
| Unit tests | `tests/unit/infra/test_r4_t4_residuals.py` |
| Contract updates | soft80 + trial exclude + 510300 basic/mf accepted empty |
| This notes | `.servo/worktrack/WT-R4-A3-t4-notes.md` |

## Non-actions (held)

- No live TuShare calls
- No pool registry mutation / no v1@2
- No cache universe expand
- No AO-O* hygiene (→ A4)
- No full-campaign

## Hand-off

- Next: **R4-A3-T5** consistency + Gate/Close packet
- Accepted residuals for Gate packaging:
  1. soft80 unmet (61 < 80; hard_cap 100 OK)
  2. 510300 basic/mf N/A (qfq filled)
  3. 601989 upstream exhausted (registry kept; trial excluded)
  4. AO-O* → A4
