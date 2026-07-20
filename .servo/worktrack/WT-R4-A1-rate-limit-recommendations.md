---
title: "WT-R4-A1 Rate Limit Recommendations"
artifact_type: "rate-limit-recommendations"
milestone_id: "MS-R4-001"
worktrack_id: "WT-R4-A1"
deliverable: "A1-D4"
status: "approved"
updated: "2026-07-20T20:52:00+08:00"
owner: "OceanEyeFF"
live_pull_in_this_artifact: "none"
account_points: 2000
approved_by: "OceanEyeFF"
approved_at: "2026-07-20T20:52:00+08:00"
approval_choice: "accept_recommended"
approved_caps:
  rpm: 180
  daily_api_calls_per_api: 80000
refs:
  - "https://tushare.pro/document/1?doc_id=108"   # 权限 / 最低分值
  - "https://tushare.pro/document/1?doc_id=290"   # 积分频次表
  - "https://tushare.pro/document/1?doc_id=40"    # pro 调取方式
  - "https://tushare.pro/document/1?doc_id=129"   # 多语言获取方式
---

# WT-R4-A1 — 日调用 / RPM 上限建议（供批准）

> **性质：** A1-T4 **建议**；A1 仍零 live。  
> **账户：** 程序员自用 **2000 积分**档（个人研究；不追求极致省配额）。  
> **依据：** TuShare 官方积分频次表（doc_id=290）+ 权限表（doc_id=108）。

## 1. Control Signal

```yaml
recommendation_id: MS-R4-001-tushare-l2-caps-v1
status: approved
approval:
  choice: accept_recommended
  approved_by: OceanEyeFF
  approved_at: "2026-07-20T20:52:00+08:00"
  caps:
    rpm: 180
    daily_api_calls_per_api: 80000
account:
  points: 2000
  tier_label: "2000以上"
  points_are_threshold_not_consumed: true   # doc_id=108：分级门槛，不扣积分
platform_limits_doc290:
  rpm: 200
  daily_per_api: 100000   # 「100000次/个API」
r4_relevant_apis_min_points:   # doc_id=108
  daily: 120
  daily_basic: 2000
  moneyflow: 2000
  # pro_bar / 复权: 2000（分钟/指数/基金/期货除外条款见官网）
approved_caps:                 # accept_recommended — 自用加大；略留平台余量
  daily_api_calls_per_api: 80000
  rpm: 180
suggested_caps:                # historical alias (= approved_caps)
  daily_api_calls_per_api: 80000
  rpm: 180
  band:
    daily_api_calls_per_api: [50000, 100000]
    rpm: [150, 200]
concurrency: 1
burst_pause_on_freq_wall: true
token: env_TUSHARE_TOKEN_only
applies_to: WT-R4-A3_and_later_limited_live
does_not_apply_to: WT-R4-A1_docs
supersedes: MS-R4-001-tushare-l2-caps-v0  # 原 300/50 过保守，已废止
```

## 2. Official Tier Snapshot（2000 积分）

摘自 [积分频次表](https://tushare.pro/document/1?doc_id=290) 表一：

| 积分数 | 每分钟频次 | 每天总量上限 | 备注 |
|--------|----------:|-------------:|------|
| 120 | 50 | 8000 次 | 非复权日线为主 |
| **2000 以上** | **200** | **100000 次 / 个 API** | R4 日频主路径落此档 |
| 5000 以上 | 500 | 常规数据无上限 | 非本账户 |

摘自 [关于权限](https://tushare.pro/document/1?doc_id=108)：

- 积分是 **调取门槛**，**不消耗积分**。  
- R4 湖主路径所需接口与 2000 档对齐示例：
  - `daily`：120 起（可用）
  - `daily_basic`：**2000 起**
  - `moneyflow`：**2000**
  - 复权 / `pro_bar`：文档写 2000（分钟/指数/基金/期货等除外，以官网为准）

调取方式见 [pro 调取](https://tushare.pro/document/1?doc_id=40) / [获取方式](https://tushare.pro/document/1?doc_id=129)：Python `ts.pro_api` 或 HTTP `api.tushare.pro`；token 仅环境变量。

**独立权限表（分钟/港美股等）与 2000 积分无关** — R4 不做分钟湖，不在本建议范围。

## 3. Recommended Caps（自用加大）

| Cap | Recommended | Band | Platform (2000) | Rationale |
|-----|-------------:|------|----------------:|-----------|
| **RPM** | **180** | 150–200 | **200** | 贴近平台上限；留 ~10% 余量防偶发突发 |
| **Daily / API** | **80000** | 50000–100000 | **100000 / API** | 个人研究不省配额；仍低于硬顶便于日志告警 |
| Max in-flight | **1** | — | — | 单 worker，避免并行把 RPM 打穿 |
| Per-batch symbols | **≤50** | — | — | 可加大批次；仍便于 resume |
| Per-batch span | 可多年窗，优先按 year 分区写盘 | — | — | 对齐 cache layout |

**相对 v0（已废止）：** 原建议 50 RPM / 300 日调用 **远低于** 2000 档能力，且与「自用不省配额」不符 → 以本 v1 为准。

**批准语义（已决）：**

- [x] **`accept_recommended`** → RPM **180**，daily/API **80000** — **approved 2026-07-20 by OceanEyeFF**
- [ ] `accept_platform_max` → RPM **200**，daily/API **100000**（未选）
- [ ] `accept_custom` / `defer`（未选）

A3 live 可消费本批准 caps；A1 仍零 live。

## 4. What Counts as One Call

| Event | Count |
|-------|------:|
| 一次 TuShare HTTP/SDK 实际发出 | +1（计入该 `api_name` 日预算） |
| 本地 cache 读 / `refresh=False` 命中 | 0 |
| 限流后的重试发出 | 每次 +1 |

日预算按 **Asia/Shanghai 日历日**、**按 API 分别计数**（对齐「100000次/个API」）。

## 5. A3 Budget Sketch（在新 caps 下）

Inventory：池 61 三表已满；主要 live 为扩 soft80 + `510300` + staleness。

| Package | 量级 | 在 80k/API·日下 |
|---------|------|-----------------|
| `510300.SH` qfq | 很小 | 可当天完成 |
| +20～40 主板 × (daily + basic + moneyflow) × 多年 | 数百～数千级（视是否按年拆请求） | **通常单日可完成** 个人扩池战役 |
| 全市场扫荡 | 禁止 | L2 仍禁止；caps 大 ≠ 允许 full-campaign |

结论：加大 caps 后，A3 **不必多日磨洋工**；仍保持 L2 宇宙边界与 evidence。

## 6. Operational Rules（建议写入 A3）

1. Dry-run 打印 (api, symbol, start, end) + 预估 calls 再 live。  
2. 达 **RPM 180** 或 **单 API 日 80000** → 停并写 evidence（若批 `platform_max` 则用 200 / 100000）。  
3. 频控 / 权限错误（如 code 2002）→ 退避或挂起；禁止 tight-loop。  
4. Universe = 批准池 ∪ 显式 expand 列表；**禁止全市场**。  
5. Token 仅 `TUSHARE_TOKEN`；禁止入仓。  
6. 分钟/港美股等独立权限接口：本里程碑 **不调用**。

## 7. Non-Goals

- A1 内 live / probe  
- 购买更高积分档或分钟权限  
- 把大 caps 解释成全市场授权  
- 训练 / EXEC-002 配额  

## 8. Approval Checklist

- [x] 接受 **180 RPM / 80000 per API·日**（`accept_recommended`，2026-07-20 OceanEyeFF）
- [x] 确认仍为 L2：无全市场 / full-campaign  
- [x] 确认 A1 继续零 live；仅 A3+ 消费本 caps  
- [x] 确认积分门槛理解：2000 不扣分，频次/日顶按 doc_id=290  

## 9. Related Artifacts

- 湖合同：`.servo/worktrack/WT-R4-A1-lake-source-contract.md`  
- Inventory / Schema：T2 / T3 交付物  
- 官方：doc_id=108 / 290 / 40 / 129  

## 10. Change Control

- v0（300/50）→ **superseded by v1**（本文件）。  
- `pending_approve` → **`approved`**（`accept_recommended`，2026-07-20 OceanEyeFF）。  
- 批准后改数值须书面记录，禁止静默再抬到越权接口（分钟等）。
