---
title: "WT-R4-A1 Consistency Matrix (T5)"
artifact_type: "doc-consistency-check"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
updated: "2026-07-20T21:08:00+08:00"
owner: "OceanEyeFF"
verdict: "consistent"
---

# WT-R4-A1 T5 — Deliverable Consistency Matrix

| Claim | D1 lake/source | D2 inventory | D3 schema | D4 rate caps | Verdict |
|-------|----------------|--------------|-----------|--------------|---------|
| Primary = TuShare, backup = AkShare | yes | n/a | n/a | n/a | ok |
| Consumer = `DataLake` only | yes (Q3) | n/a | references develop adapter | n/a | ok |
| Pool = `custom_research_liquidity_quality_v1@1` / 61 | yes | 61/61 cover | join keys bare↔ts_code | n/a | ok |
| History start 2023-01-01 | yes | date_min≈2023-01-03 | yes | n/a | ok |
| Layout `tushare_*/{ts_code}/year=/part.parquet` | yes | scanned | frozen | n/a | ok |
| qfq default; amount = 千元 | yes | n/a | yes | n/a | ok |
| soft80 unmet → A3 | residual | G1 | n/a | budget sketch | ok |
| `510300.SH` empty → A3 | defer | G2 | deferred schema | fill in budget | ok |
| A1 zero live / no cache write | yes | yes | yes | yes | ok |
| Caps 180 rpm / 80k per API·day | pointer | n/a | n/a | **approved** | ok |
| No Phase4 / EXEC-002 / train | yes | yes | yes | yes | ok |
| Caps later → fixed repo file | deferred A2/A3 | — | — | noted | ok |

**Inconsistencies found:** none blocking.  
**Doc hygiene:** D1–D3 remain `draft` until Gate freeze; D4 already `approved`.
