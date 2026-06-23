---
title: "WT-S2-A2 Registry Schema Gap Report"
artifact_type: "worktrack-evidence"
milestone_id: "MS-S2-001"
worktrack_id: "WT-S2-A2"
updated: "2026-06-22T10:48:41+08:00"
owner: "OceanEyeFF"
---

# WT-S2-A2 Registry Schema Gap Report

## Conclusion

- current_registry_status: pass for frozen symbol-list sample pools.
- stratification_manifest_status: gap for full MS-S2 stratification metadata.
- recommendation_for_A3: use existing `custom_*` registry records for minimal samples, and place `data_end_date`, `source_endpoints`, and `fetch_manifest` in `notes` or a sidecar manifest unless A3 explicitly extends the schema.
- dedicated_family_status: no dedicated `strat_*` family exists; adding one is optional and should not block minimal A3 samples.

## Current Supported Fields

- `stock_pool_id`
- `stock_pool_version`
- `pool_family`
- `pool_label`
- `construction_method`
- `base_universe`
- `symbols_source`
- `symbols_count`
- `rebalance_frequency`
- `effective_start`
- `effective_end`
- `is_default`
- `is_research_only`
- `owner`
- `notes`
- optional `symbols_csv`

## Gaps For MS-S2 Stratification

The current schema does not have first-class fields for:

- `data_end_date`
- `source_endpoints`
- `fetch_manifest`
- proxy field set and threshold window
- cache coverage summary
- blocked-by-data / blocked-by-quota reason
- layer type such as large-cap proxy, low-control-proxy candidate, or suspected-control observation

## A3 Guidance

- Do not use colloquial IDs in formal metadata.
- Keep low-control-related samples `is_research_only=true`.
- Use `custom_low_control_proxy_candidate_*` or similar `custom_*` IDs unless A3 adds a validated family extension.
- Record fetch manifests produced by `plan_tushare_fetch_manifest` before any sample pool depends on missing TuShare data.
- If required fields are not cached and quota approval is absent, produce `blocked-by-data` / `blocked-by-quota` instead of a synthetic sample pool.
