---
title: "WT-S2-A3 Closeout Report"
artifact_type: "worktrack-closeout-report"
milestone_id: "MS-S2-001"
worktrack_id: "WT-S2-A3"
updated: "2026-06-22T12:15:00+08:00"
owner: "OceanEyeFF"
---

# WT-S2-A3 Closeout Report

## Control Signal

- worktrack_id: WT-S2-A3
- milestone_id: MS-S2-001
- closeout_status: closed
- gate_verdict: pass
- next_route: WT-S2-A4 intake/init (下游复验输入契约、请求预算与收尾报告)

## Accepted Changes

### New Files

- `scripts/build_ms_s2_stratified_pools.py` — 从 TuShare daily_basic 缓存构造分层股票池的 cache-only 脚本
- `configs/stock_pools/custom_liquid_large_proxy_v1.toml` — 大盘流动性 proxy 锚点池 registry 配置
- `configs/stock_pools/custom_liquid_large_proxy_v1_symbols.csv` — 5 只股票符号列表
- `configs/stock_pools/custom_liquid_large_proxy_v1_metadata.json` — 构造元数据 sidecar
- `configs/stock_pools/custom_low_control_proxy_candidate_v1.toml` — 低控盘 proxy 候选池 registry 配置
- `configs/stock_pools/custom_low_control_proxy_candidate_v1_symbols.csv` — 3 只股票符号列表
- `configs/stock_pools/custom_low_control_proxy_candidate_v1_metadata.json` — 构造元数据 sidecar

### Pool Details

#### custom_liquid_large_proxy_v1（大盘流动性 proxy 锚点池）

| 字段 | 值 |
|---|---|
| 构造方法 | cache-only from TuShare daily_basic; universe filter excludes 688/300/301/8/4; total_mv >= 5000 亿 |
| 基准池 | TuShare daily_basic cache (8 symbols), A-share mainboard only |
| 股票数 | 5 |
| 股票列表 | 000333, 002594, 600036, 600519, 601318 |
| 排除 | 300750（创业板）、000001/000858（市值未达 5000 亿阈值） |
| is_research_only | false |
| 数据截止日 | 2026-03-05 |
| 数据端点 | daily_basic |
| 获取清单 | cache-only; no quota-consuming call |

#### custom_low_control_proxy_candidate_v1（低控盘 proxy 候选池）

| 字段 | 值 |
|---|---|
| 构造方法 | cache-only; parent pool: custom_liquid_large_proxy_v1; avg_turnover_rate < 0.5 |
| 基准池 | custom_liquid_large_proxy_v1 |
| 股票数 | 3 |
| 股票列表 | 000333, 600036, 600519 |
| is_research_only | true |
| 数据截止日 | 2026-03-05 |
| proxy 声明 | turnover_rate is a proxy; does not measure true control probability |

## Validation

- `PYTHONPATH="src:." conda run -n "py311-private" python scripts/build_ms_s2_stratified_pools.py` -> 成功生成 2 个 TOML + CSV + metadata
- Registry load: `load_stock_pool_registry()` -> 3 records (含原有 custom_quick8_v1) 全部通过
- Individual lookup: 两个新池均通过 `get_stock_pool_record()` 验证
- Export smoke: `export_stock_pool_artifacts()` -> symbols.csv + metadata.json 均成功导出
- `git diff --check` -> pass
- `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_tushare_source.py` -> 14 passed（现有测试未受影响）

## Residual Risk

- 缓存仅覆盖 8 只股票（quick8 集合），样本量有限；后续研究需要更广的缓存覆盖或审批后的 quota-consuming 获取
- 创业板 300750 被 universe filter 排除，002594（中小板）仍在池中——002* 不在当前排除规则中
- 低控盘候选池的 turnover_rate 阈值（< 0.5%）是初始设定，未经 3/5/10d 复验校准
- 未发起任何 TuShare quota-consuming 调用——所有数据来自现有缓存
- 未做模型训练、信号晋级或回测验证

## Non-Goals Preserved

- ✅ 未做 3/5/10d 复验
- ✅ 未做模型重训
- ✅ 未做信号晋级
- ✅ 未做生产数据刷新
- ✅ 未发起 TuShare quota 调用
- ✅ 未从小盘/疑似控盘层构造样本
- ✅ 未从样本注册膨胀为研究结论
