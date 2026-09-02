# 下一步工作安排（Next Steps）

> 2026-08-13 | 双路 CodeReview 修复后 | 本文档是唯一执行入口，任务按编号逐项推进

## 当前状态

项目已完成 R2（三区布局）→ R3（旧文件清理）→ T1（测试体系）→ R4（TuShare 数据湖合同）。
2026-08 完成换机后的环境重建、akshare 移除、双路 CodeReview 与 P0 缺陷修复：

- **环境**：`py311-private`（Python 3.11 + PyTorch cu130，RTX 3080 Ti GPU 可用）
- **数据源**：TuShare 单一信源（akshare 已完全移除，含负向合同测试）
- **测试**：1020 passed / 10 skipped，覆盖率 77.13%（门禁 76）
- **数据湖**：R4 合同冻结，但 `inputs/data/cache` **尚未落盘**（P0-①）
- **选股池**：`custom_research_liquidity_quality_v1`（60 只，research_only；2026-08-13 剔除停牌股 601989.SH）已注册

## 执行纪律

- 每个任务**独立提交**，提交前全量测试 + 覆盖率不回退
- 债务类任务（D*）**禁止与功能改动混合提交**
- 每完成一个任务，更新本文档勾选状态并标注日期
- 提交/推送须经程序员批准（docs/WORK_RULES.md）

---

# P0 执行清单：把主线预测做"可信"

## 阶段 0 — 穿插性基础任务（与主线并行，可随时穿插）

### ☑ T0-A [D6] 本地噪音清理（~10 分钟）— 2026-08-13 完成
- 删除 gitignored 历史文档 `.claude/specs/`、`.autoworkflow/`（含 akshare/旧路径字样，仅本机噪音）
- 连带删除同类遗留：`.bmad-core/`、`.spec-workflow/`、`.claude/commands/`（程序员确认一并删除）
- 验收：`git status` 无变化；本机目录已清

### ☑ T0-B [D1] 配置格式统一 — 并入阶段 2.0 完成（2026-08-13）
1. `inputs/configs/{pipeline,data_source}.toml` + `profiles/model_mtl.toml` 由 YAML 内容转真 TOML
2. `scripts/daily_pipeline.py:_load_yaml` → tomllib；`scripts/train_mtl.py` yaml.safe_load → tomllib
3. 新增合同测试：`inputs/configs/**/*.toml` 全部可被 `tomllib.loads` 解析
4. `test_model_mtl_yaml_parses` 改名/改实现
- 验收：全量绿 + grep 确认无 yaml 解析 .toml + `daily_pipeline --dry-run`、`train_mtl --dry-run` 通过

### ☐ T0-C [D4-A] ruff 机械批（~2 小时）
- `ruff check --fix --select I001,B009,UP006,PLR0402`；RUF100 逐条复核 noqa 是否仍必要
- 验收：该批规则计数归零、全量绿（独立提交）

### ☑ T0-D [D5] 测试深度补强 — 2026-08-13 完成
1. ✓ 新增 `tests/contract/recommendation/test_adapter_kwargs_contract.py`（9 项）：make_r4_datalake 构造参数透传、load_daily_bars 的 source/adjust/日期规范化、ODP odp_* 字段、HS300 日期规范化、三 adapter 拒绝未知 kwargs
2. ✓ `test_infra_a_flow.test_i1` 改薄 shim 委托**真实** load_or_fetch_daily_bars 读写链路（fetch 哨兵防触网，不再内联重实现读取）
3. ✓ 新增 `test_i1b_weekend_gap_no_rows`：周末缺口用例 + 与 manifest calendar 一一对应
- 验收：全量 1050 passed；覆盖率 77.11%

### ☐ T0-E [D4-B] ruff 手动批（~3 小时）
- F401（确认无副作用导入）/UP035/RUF046/SIM118/FLY002/SIM102 逐文件小修
- 验收：该批计数归零、全量绿（独立提交）

### ☐ T0-F [D4-C] ruff 语义批（~2 小时，与 P0-④ 联动）
- BLE001/TRY004/DTZ005/DTZ007 逐处评审；先明确时区约定（建议：naive 北京时间 + 注释或 per-file-ignores）
- 验收：剩余项全部有明确 noqa 理由；全量绿（独立提交）

### ☐ T0-G [D3] deployment install.sh 模板化（~1 小时，下次换机/部署前完成即可）
1. service 路径改 `PROJECT_ROOT` 占位符；新增 `deployment/install.sh`（接收部署机路径 sed 替换 + TUSHARE_TOKEN 非占位校验）
2. `test_deployment_files.py` 锁定占位符机制；ops 文档补充 install.sh 用法
- 验收：换路径部署只需跑 install.sh；测试锁定

---

## 阶段 1 — P0-① 数据湖落盘（批准池 60 只 limited-live）

### ☑ 1.1 限流与权限确认（~15 分钟）— 2026-08-13 完成
- 已核对 TUSHARE_TOKEN 有效（56 位）；实测 6 接口全部有权限：daily / fund_daily / adj_factor / daily_basic / moneyflow / index_daily
- 限流：L2 caps（rpm 180，daily 80000/api）已由 acquire_tushare_call 生效
- **关键发现**：510300.SH 是 ETF——`pro.daily`/`adj_factor`/`daily_basic`/`moneyflow`/`index_daily` 对 ETF 均返回空；`fund_daily` 有数据（代码已实现回退）。真正指数日线锚点用 000300.SH
- 验收：权限清单记录在案；无权限接口提前降级

### ☑ 1.2 锚点验证（~20 分钟）— 2026-08-13 完成
- 五链路小窗口（20240102-20240105）全部落盘验证通过：
  - 510300.SH（ETF）→ fund_daily 回退 ✓（close 3.453→3.396 合理）
  - 000300.SH 指数 → index_daily ✓（3386.35→3329.11 合理）
  - 600519.SH 股票 → daily+adj_factor qfq 复权 ✓（1685→1663 合理）
  - daily_basic（9 列）/ moneyflow（18 列）✓
  - **pandas 3.0.5 全链路无兼容问题**
- 落盘布局符合 R4 合同：`tushare_qfq/{ts_code}/year=YYYY/part.parquet`、index CSV、`tushare_daily_basic/`、`tushare_moneyflow/`
- 合同测试反馈：test_r4_cache_schema_contract 从 10 skip → 6 passed + 7 failed（失败均为“全池未落盘”，1.3/1.4 完成后转绿，非 schema 漂移）
- 验收：锚点数据落盘，schema 符合 R4 合同

### ☑ 1.3 全池 qfq 日线拉取（~1-2 小时，受限流支配）— 2026-08-13 完成
- 60 只（原 61，601989.SH 停牌剔除）× 2023-01-01..2026-08-13，用 `tushare_batch`（chunk_symbols 分块 50+10，manifest 续传，freq-wall 自动暂停）实际耗时 ~10 分钟，failed=0
- cache-first：lake refresh=False + 增量拉取，重复运行不重拉
- QA（workspace/runs/r4_fill_qfq_validation.json）：60/60 完整——875 行、2023-01-03→2026-08-13、nan_ratio=0
- **601989.SH 已于当日剔除**（与中国船舶吸收合并，2025-08-12 起停牌）：池 61→60，合同常量 R4_SYMBOLS_COUNT=60，缓存分区已删
- 合同测试：qfq 覆盖已转绿（9 passed）；剩余 4 failed 为 daily_basic/moneyflow 未拉（1.4 范围）
- 验收：60/60 落盘，无缺洞

### ☑ 1.4 daily_basic + moneyflow 拉取（~1-2 小时）— 2026-08-13 完成
- 同池同窗口，同样 tushare_batch 分批续传，failed=0，实际 ~4 分钟
- QA（workspace/runs/r4_fill_bm_validation.json）：moneyflow 60/60 全 ok；daily_basic 49/60 ok，11 只 nan_ratio 0.01-0.11——全部集中在 pe_ttm（亏损期无 PE）/dv_ttm（无分红）两字段，TuShare 官方自然缺失，非管道缺陷
- 验收：60/60 落盘，与 qfq 分区对齐

### ☑ 1.5 落盘 QA 与 manifest（~30 分钟）— 2026-08-13 完成
- 三 namespace 全池完整：tushare_qfq 61 分区（60 池 + 510300 锚点）、daily_basic 60、moneyflow 60，missing=[]
- cache-first 验证：make_r4_datalake(refresh=False) 全池读取零缺失（增量只补缺）
- **合同测试 13/13 全绿**（历史 10 skip + 7 中间态失败全部转正）；全量测试 1030 passed / 0 failed / 0 skipped
- 验收：数据湖对全池 cache-first 可用；阶段 2（合同增强）可以开始

## 阶段 2 — P0-② 合同测试恢复与增强 [D2]（紧随 1.5，~2 小时 + 前置 D1）

### ☑ 2.0 [D1] 配置转真 TOML — 2026-08-13 完成
- 3 配置转写完成（注释全保留）；消费方 daily_pipeline/train_mtl → config_io.load_mapping_config（scripts/ 双 import 兼容）、orchestrator/core.py → tomllib(+tomli fallback)
- 4 处测试同步（含 tests/support/toml_utils.py 新助手）；合法 YAML 场景保留（metadata.yaml、load_yaml 工具）
- 验收：6 个 configs 全部 tomllib 可解析；全量 1031 passed；覆盖率 77.11%
- 转写：`pipeline.toml`、`data_source.toml`、`profiles/model_mtl.toml`（保留全部注释）
- 切消费方：`scripts/daily_pipeline.py` / `scripts/train_mtl.py` 的 `_load_yaml` → `config_io.load_mapping_config`；`orchestrator/core.py` yaml.safe_load → tomllib(+tomli fallback)
- 同步测试：`test_profile_paths_contract`（model_mtl 段）、`test_daily_pipeline_prod` fixture（JSON 伪 YAML → TOML）、`test_pipeline.py`（yaml.dump → TOML）、`test_models.py:434`
- 保留合法 YAML 场景：`mtl_finetune.load_yaml` 工具函数、builder metadata.yaml
- 验收：`tomllib` 能解析全部 6 个 configs；无 YAML 假 TOML 残留；全量绿

### ☑ 2.1 skip → 硬断言 — 2026-08-13 完成
- `_require_cache` 由 pytest.skip 改硬断言（缺失即合同违约）；13/13 真实通过
- 唯一保留 skip：derived 树（T2 前可选，合同设计语义，非 cache 合同）

### ☑ 2.2 深度增强 — 2026-08-13 完成
- 全池×全分区遍历：60 只 × 3 namespace × 全部 year= 分区，schema/年份对齐/非空硬断言
- 起点锁定：全池 earliest ∈ [2023-01-01, +31d]（不再抽样 5 只）
- 连续性：gap>15 自然日即失败，豁免登记制——全池 4 处断档全部经 TuShare suspend_d 官方记录验证后登记（002554/600150/601088/603019，真实停牌）
- 尾部新鲜度 ≤21d；目录双向一致（qfq=池∪{510300}，basic/mf=池）
- 测试即时抓到 603019/600150/601088/002554 四只真实停牌——合同测试有效性实证
- 验收：20/20 通过（注入漂移可拦截：已实际拦截 4 处非豁免断档）
- 遍历全部 symbols/parts；锁定历史起点（≈2023-01 首个交易日，合理容差）与连续性（交易日缺口检查——自然断档豁免表：长假/停牌）；manifest 与分区文件集合交叉校验
- 真实 loader 消费 fixture：fixture 不手工拼 parquet，改走 `load_or_fetch_daily_bars` 真实写入链路（离线 seam）
- 验收：人为注入 schema 漂移/缺数可被拦截

### ☑ 2.3 双层防护成立 — 2026-08-13 完成
- 第 1 层 seeded fixture（永不 skip，0 处 pytest.skip）：schema/布局/无旧布局 + **真实 loader 链路 offline round-trip**（D5：fetch seam→_write_partitioned→读回，锁定写读链路本身）
- 第 2 层真实湖（cache 缺失即合同违约，0 处 skip）：2.1+2.2 全部硬断言
- 验收：contract/infra 154 passed；全量 1039 passed；覆盖率 77.11%

## 阶段 3 — P0-③ 评估范式固化（~1 天）

### ☑ 3.1 Daily-CS IC/RankIC 基线复跑 — 2026-08-14 完成
- 数据集重建：`sequence_baseline_20230101_20260813`（60 只 × 11 特征 × seq20，test 2026-02-09..2026-08-13；profile end 同步 20260813）
- LSTM（auto 特征）+ XGB 滚动重训 → OOS parquet + 报告 → audit + compare + sanity（h5/h10）
- 基线结论：**continue-research**——RankIC 0.0664/0.0769 < 0.08（XGB 距门禁 0.0031）；time_reverse 部分未过；lag-1 阈值对 daily 重预测判别力弱（记入协议修订项）
- 数字留档：协议文档 §7 Baseline Ledger；产物 outputs/reports/（本地 artifact）
- 修复过程中发现：rolling 脚本 feature-mode 默认 dim19 与新数据集 11 特征不匹配 → 用 --feature-mode auto；XGB 依赖补装

### ☑ 3.2 月胜率分布 + trade-like Top-N 面板 — 2026-08-14 完成
- 新脚本 `scripts/compare_trade_like_panels.py`：panel 汇总 + 逐月超额收益矩阵 → outputs/reports/ic_trade_panel_<tag>.md（2 项 CLI 合同测试锁定）
- 基线面板结论：XGB **pass**（日胜率 60.2%、月胜率 66.7%、连续负月 1）；LSTM **fail**（日胜率 44.2%、连续负日 19 天——重要风险信号）
- 与 IC 门禁互补：XGB RankIC 差 0.0031 未过 strict 门禁，但 panel 无相反风险信号；整体维持 continue-research

### ☑ 3.3 评估门禁协议执行版 — 2026-08-14 完成
- 协议文档更新：路径三区对齐（outputs/reports）、§6b 新增执行版命令链（build→rolling→audit→compare→panel→sanity，全部实测）、§7/§8 基线 ledger、random-label/neutralization 缺口声明更新
- 逐条照抄实测：audit/compare/panel/sanity（含 random-label 3 trials 全 pass）均产出预期文件
- 验收达成：文档命令可照抄执行，产物清单完整

## 阶段 4 — P0-④ 伪信号系统性排查（2026-08-14 ~ 09-02 完成）

### ☑ 4.1 标签起点对齐审计 — 2026-08-14 完成（verdict=PASS）
- 新脚本 `scripts/audit_label_alignment.py`（可重复）+ workspace/runs/audit_label_alignment.json
- label 全精确（≤1.4e-8）；1d 标签精确；maturity date 按交易日 shift 正确
- **无未来泄漏**：窗口 [t-seq_len, t-1]（builder 合同）+ 特征自身 shift(1) → 双重保守（date 行=截至 t-2 信息），解释基线 IC 偏低因素之一
- **决策记录**：close_to_close 评估口径高估可交易性 → 5.x 前升级 next_open_to_open（或双口径对照）
- 补充：审计脚本需 source .env（未 source 会假报警）

### ☑ 4.2 sanity checks 三件套 — 2026-08-14 完成（verdict：主信号优于随机，无伪信号迹象）
- shuffle：全 pass（LSTM/XGB）
- time_reverse：稳定负 IC（XGB h10 -0.0436 × 3 seeds）——负值非泄漏特征（正 IC 保持才是）；协议判据修订
- lag-1：阈值设计缺陷（daily 窗口重叠 90%+）→ 新脚本 `scripts/audit_lag_horizon_analysis.py`（daily-CS 口径 lag-h 非重叠对照，+1 CLI 合同测试）
- lag-h 时效表：XGB/LSTM h10 单调衰减（0.085→0.004 / 0.076→0.009），XGB h5 lag5 回升为噪声区间（IC≈0）
- 假象排除：个股内时序 corr 混合横截面信号会呈"lag 递增 IC 上升"——已记录禁用口径

### ☑ 4.3 复权/停牌/涨跌停审计 — 2026-08-14 完成（2 个 P1 缺陷已修复）
- **P1-1 行间停牌标签污染**（multi_horizon.py）：停牌日无行 → 停牌前 label 用复牌后价格（601088 8-01 label_5d=0.0250 实为 18 天跨停牌收益）；修复 `_suspension_gap_mask`（断档>15 天=停牌），停牌股各 ~30 NaN，+2 单元测试
- **P1-2 qfq 增量边缘整段重取**（tushare_source.py）：元旦边缘增量区间 → qfq 分支整段重取 865+ 天（每次读取触发）；修复为前端边缘增量拼接（尾部/中洞仍整段）
- 涨跌停：t 涨停日 close_to_close 标签买入不可行 → 并入 4.1 的 next_open 升级决策
- **后续动作（已完成）**：数据集重建（51235 样本）+ 双基线重跑（v2）——v1→v2 对照证实跨停牌污染贡献伪信号
- 全量 1063 passed

## 阶段 5 — P0-⑤ 模型同窗比较（2026-09-02 完成）

### ☑ 5.1 LSTM / XGBoost 同窗同标签训练 — 2026-09-02 完成
- 同数据集（sequence_baseline_20230101_20260813）同窗口（rolling 26 周）同标签（close_to_close 3/5/10d+1d）训练 LSTM/XGB
- 产物：训练日志（workspace/runs/3.1_*_v2.log）、OOS parquet、报告 JSON（outputs/reports/*_v2*）
- checkpoint 说明：rolling 脚本支持 --save-weekly-checkpoints；认证（P1 certified.json）时必选，认证前无消费方（记入 P1 前置）

### ☑ 5.2 IC/收益一致性结论 — 2026-09-02 完成
- 结论报告：outputs/reports/5.2_same_window_comparison_v2.md
- **两模型均未过认证门禁**（RankIC 0.0649/0.0596 < 0.08；panel 均 fail）→ certified.json 落**明确否决记录**（status=rejected + 理由 + candidates 快照）
- 主模型无唯一解：IC 口径 LSTM 略优（RankIC 0.0649 vs 0.0596）；trade-like 口径 XGB 更稳（连续负日 9 vs 19、月胜率 50% vs 33%）；均不显著
- LSTM 连续负日 19 天真实交易不可接受（即使 RankIC 略高）
- alpha_score 维持 candidate research signal（协议 §5）；P1 按窗口/重训/loss 实验后重新评估认证

---

## P1（阶段 5 通过后）：主线性信号优化

1. 窗口长度、重训频率、loss 权重实验
2. `pred_3d/pred_5d/pred_10d → alpha_score` 聚合契约固化
3. 认证模型配对 → `workspace/registry/certified.json`

## P1.5 联调复现性审计（2026-09-02 完成）

- 审计报告：`docs/research/reproducibility_audit.md`——数据→数据集→模型→评估 全链路
- ✅ 已验证：数据集重建 metadata 完全一致（两次构建）；sanity 同 seed 重跑逐字段一致；评估链（audit/compare/panel）确定性且 repro 产物与基线数字**逐字节一致**
- ✅ 修复 G1：LSTM cudnn.deterministic=True（CUDA 重训可复现）
- ✅ 闭环 G2：`scripts/repro_full_chain.sh`（--dry-run / --skip-training / 全链路）一键入口，skip-training 实测跑通
- 规范：产物比对忽略 generated_at/created_at 时间戳；nohup 用 `python -u`

## P2（后续）：扩展

1. `1d` 分钟级数据可用性验证
2. 决策模型 I/O 协议冻结
3. 生产调度监控（deployment 全链路 + T0-G 落地）

## 当前明确不做

- 不把 `1d` 并入主线打分
- 不用日 K-only 给 `1d` 下最终结论
- 不在主线通过可信门禁前做复杂决策逻辑
- 不上新闻/公告/事件 embedding

---

## 关联文档

- 长期路线：[ROADMAP.md](ROADMAP.md)
- 全局工作规则：[docs/WORK_RULES.md](docs/WORK_RULES.md)
- 文档总导航：[docs/README.md](docs/README.md)
- 主线评估门禁：[docs/research/mainline_3510d_evaluation_gate_protocol.md](docs/research/mainline_3510d_evaluation_gate_protocol.md)
- Daily-CS 工作流：[docs/research/daily_cs_eval_workflow.md](docs/research/daily_cs_eval_workflow.md)
- 研究清单：[docs/research/research_checklist.md](docs/research/research_checklist.md)
