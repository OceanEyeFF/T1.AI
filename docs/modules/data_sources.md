# 数据源选型与接入说明

本文档补齐仓库中的数据源引用入口，给出当前可用的最小接入策略。后续可在不改动交易协议的前提下逐步扩展。

## 1. 设计原则

- 与交易/回测层解耦：统一遵循 `../interfaces/data_contract.md`。
- 优先稳定可复现：同一实验期内固定数据口径。
- 先日频后扩展：先保证日线行情与基础因子链路稳定。

## 2. 当前推荐组合

### 2.1 基础行情与财务

- 首选：TuShare Pro（覆盖完整、字段规范化较好）
- 备选：AkShare（快速验证、开源接口丰富）
- 扩展：OpenBB ODP（支持跨市场资产，含国际大宗商品/外汇/指数等）

### 2.2 指数与基准

- 沪深300等基准指数优先使用与主行情一致的数据源，避免口径漂移。

### 2.3 另类数据（可选）

- 北向资金、行业板块、宏观代理变量等作为增量输入，不应破坏主流程可复现性。

## 3. 接入约束

- 所有外部字段在进入训练前必须映射到 `../interfaces/data_contract.md` 定义。
- 严禁混用复权口径（qfq/hfq/raw）而不显式标注。
- 训练集与评估集必须使用同一版本的数据快照策略。

## 4. 最小执行建议

1. 研究环境先用 AkShare 跑通全链路。
2. 稳定阶段切到 TuShare 做长期回测与产线化。
3. 跨市场因子（如国际商品）可通过 ODP 接入，并与 A 股主行情分层管理（主行情与扩展因子解耦）。
4. 每次切换数据源必须产出对比报告（覆盖率、缺失率、IC 变化）。

## 5. ODP 接入说明（新增）

- 代码入口：
  - `src/ashare_lab/data/odp_source.py`（SDK 优先，REST 兜底）
  - `src/ashare_lab/recommendation/validator.py::ODPSourceAdapter`
  - `scripts/daily_pipeline.py`（`default_source: odp`）
- 配置入口：`configs/data_source.yaml -> sources.odp`
- 运行要求（二选一）：
  - 安装 `openbb` Python SDK；
  - 或本机/内网可访问 ODP REST API（通过 `ODP_BASE_URL` 指向服务地址）。

## 6. 阶段性结论（截至 2026-03-06）

在当前实验范围内（A 股 `quick8` 股票池，滚动周频重训，`2023-01-01` 到 `2026-03-05`），引入 ODP 国际大宗商品特征后：

- `raw` 指标有阶段性提升，但
- `calibrated` 主指标（`avg_ic`、`avg_rank_ic`）相对基线明显回落。

并且将国际大宗缩窄到“能源+金属”子集后，结果仍未超过纯 A 股基线模型。
进一步将商品因子切换到 TuShare 国内期货（`fut_daily`）后，`raw` 指标有改善，但 `calibrated` 主指标仍未超过基线。

因此当前工程结论为：

1. 国内二级市场在本策略与样本范围内，对国际大宗价格因子的敏感性偏弱。
2. 国际大宗因子暂不作为默认训练输入，仅保留为可选扩展与监控项。
3. 默认仍以国内行情与资金流因子为主，避免因跨市场噪声拉低校准后稳定性。
4. 国内期货商品因子保留在候选池，后续仅在“校准策略重构”后再复评是否纳入默认特征。

对应报告：

- `output/reports/lstm_dim53_no_hist_hl_auto_window24_seq20_icaware_a0176_lr5e5_coswrt_pat20_seed042_20260305_latest.json`
- `data/datasets/archives/reports_odp_abtests_20260306.tar.gz`（包含以下报告：
  - `output/reports/abtest_odp_cmdty_dim58_bestparams_20260306.json`
  - `output/reports/abtest_odp_cmdty_energy_metals_dim58_bestparams_20260306.json`
  - `output/reports/abtest_tushare_fut_cmdty_dim58_bestparams_20260306.json`
  - `output/reports/ic_monthly_comparison_20260306.json`
  - `output/reports/ic_monthly_comparison_tri_compare_cmdty.json`
  - `output/reports/ic_monthly_comparison_tri_compare_cmdty_raw.json`
  - `output/reports/ic_monthly_comparison_quad_compare_cmdty.json`）

## 7. 补充结论（截至 2026-03-07）

在同一评估窗口下补充了 XGBoost 滚动重训对照（与 LSTM 保持同一数据切分口径）：

- 基线（53 维）：
  - LSTM：`calibrated avg_ic=0.080951`，`avg_rank_ic=0.062236`
  - XGBoost：`calibrated avg_ic=0.100764`，`avg_rank_ic=0.131346`
- 加入国内期货商品因子（58 维，TuShare `fut_daily`）：
  - LSTM：`calibrated avg_ic=-0.005610`
  - XGBoost：`calibrated avg_ic=-0.174614`

阶段性判断：

1. 在当前样本和训练配置下，XGBoost 在纯 A 股基线特征上优于 LSTM。
2. 国内期货商品因子加入后，两种模型的校准后表现均下降，且 XGBoost 下劣化更明显。
3. 因此“国内商品因子默认并入”仍不成立，继续作为可选扩展项，不进入默认训练配置。

另外，本日（2026-03-07）对 TuShare 国内期货做了额度刷新后的重新抓取验证，重建数据集与旧版本 `train/valid/test/metadata` 的文件哈希一致，说明当前实验输入未发生变化。

本轮整理后保留的最佳测试结果：

- `output/reports/lstm_dim53_no_hist_hl_auto_window24_seq20_icaware_a0176_lr5e5_coswrt_pat20_seed042_20260305_latest.json`
- `output/reports/lstm_dim53_no_hist_hl_auto_window24_seq20_icaware_a0176_lr5e5_coswrt_pat20_seed042_20260305_latest_oos.parquet`
- `output/reports/abtest_xgb_baseline_dim53_20260306.json`
- `output/reports/abtest_xgb_baseline_dim53_20260306_oos.parquet`

其余测试结果已归档到：

- `output/reports/reports_nonbest_experiments_20260307.tar.gz`
