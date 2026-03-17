# 主模型同步后的优化工作计划（2026-03-11）

## 1. 目的

本计划承接：

- `develop` 已快进同步 `feature/model-3d-5d-10d-head`
- 审计结论见 `docs/overview/branch_consolidation_audit_20260311.md`

本计划只聚焦**当前必须做**的事项，不展开可延期优化项。目标有三类：

1. 稳住刚同步进 `develop` 的主模型能力基线；
2. 处理审计文档中已经明确的后续必做事项；
3. 把重复沟通最多的流程问题固化为标准动作。

补充定位：

- `develop` 在本轮后续工作中，主要承担集成、架构、审核和吸收门禁职责；
- 细节研究、长周期调参和大规模实验矩阵，原则上继续留在对应功能/研究分支推进；
- 对必须在 `develop` 落地的 dependency，只推进接口、registry、版本规则和验收标准，不把主线再次扩成研究沙盒。

---

## 2. 当前前提

### 已完成事实

- `develop` 已同步到 `feature/model-3d-5d-10d-head` 的 HEAD（`f6cb27a`）
- 主模型最小回归测试已通过：

```bash
PYTHONPATH=src:. pytest -q \
  tests/test_trade_like_panel.py \
  tests/test_trend_aggregation.py \
  tests/test_trend_schema.py \
  tests/test_lstm_dynamic_heads.py \
  tests/test_multilevel_tuning.py
```

结果：`25 passed`

### 当前立即风险

1. 测试运行入口尚未标准化，裸跑 `pytest` 仍可能导入失败。
2. `feature/model-d1-research` 尚未对齐新的 `develop`。
3. `feature/execution-layer-v2` 的价值仍停留在设计文档，未进入实现闭环。
4. 主模型虽然已入基线，但 `LSTM/XGBoost` 主线 baseline 闭环仍未完成。

---

## 3. 总体优先级

按优先级划分，本轮必须做的工作流如下：

| 优先级 | 工作流 | 目标 |
|--------|--------|------|
| `P0` | 测试入口标准化 | 消除同步后最直接的运行不确定性 |
| `P1` | 股票池模组开发立项与第一阶段实现 | 解决后续主模型与 `1d` 扩展的上游 dependency |
| `P1` | 股票池模组基线与双窗口协议 | 固定数据/股票池 contract，避免后续实验口径继续漂移 |
| `P1` | 主模型 baseline 闭环继续推进 | 让新并入的主模型能力真正可用 |
| `P1` | `model-d1-research` 对齐与吸收准备 | 收敛下一条代码/研究分支 |
| `P1` | 执行层设计资产规范化吸收 | 回收执行层方案价值，但不误判为已实现 |
| `P2` | 分支启动与文档流程基线 | 压低后续反复确认成本 |

说明：

- 上表中的 `develop` 工作，应优先理解为“架构统一、审核闭环、吸收门禁”，而不是继续在主线上开展具体研究实现；
- 即便需要推进股票池模组，也先做 dependency 级骨架和接线基线，不在 `develop` 上直接铺开大规模策略实验。

---

## 4. Phase O0：测试入口标准化

## 4.1 目标

把“如何在当前仓库里正确跑测试”变成统一规则，而不是个人经验。

## 4.2 必做任务

1. 固定仓库级测试入口约定：
   - 推荐主命令：`PYTHONPATH=src:. pytest -q ...`
   - 如决定改为 `python -m pytest -q ...`，必须统一替换说明
2. 明确最小 smoke test 集合：
   - 主模型 smoke
   - `1d` 研究 smoke
   - 后续执行层 smoke
3. 选择一种可复用载体：
   - 文档规范
   - `Makefile`/脚本封装
   - 或两者同时存在
4. 在项目入口文档中只挂“测试规范入口”，不在多个入口页复制长命令。

## 4.3 建议涉及文件

- `README.md`
- `docs/README.md`
- 新增：`docs/overview/testing_baseline_20260311.md`
- 可选新增：`scripts/run_smoke_tests.sh`

## 4.4 验收标准

- 任意人在仓库根目录能用单一标准命令跑通主模型 smoke；
- 文档中不再同时存在多种互相冲突的测试入口；
- 新增模块后，不再因为路径问题出现误判性失败。

---

## 5. Phase O1：主模型 baseline 闭环继续推进

## 5.1 目标

把刚同步进 `develop` 的主模型能力，从“已并入”推进到“已形成稳定主线基线”。

## 5.2 必做任务

1. 完成 `LSTM` 真实主线数据上的 baseline vs candidate 对照。
2. 明确当前 `LSTM` 默认配置所处状态：
   - `baseline`
   - `candidate-best`
   - `frozen-best`
3. 建立 `XGBoost` 主模型 baseline：
   - 同一 OOS 窗口
   - 同一主指标
   - 同一报告结构
4. 产出 `LSTM vs XGB` 同口径统一比较结果。
5. 保证主线统一评估继续以 `trade_like panel` 为默认解释口径。

## 5.3 建议涉及文件

- `configs/experiments/lstm_rolling_baseline.toml`
- `scripts/run_lstm_rolling_retrain_dim19_regime.py`
- `scripts/run_xgboost_rolling_retrain_regime.py`
- `scripts/compare_ic_reports.py`
- `docs/research/mainline_3510d_model_development_plan_20260310.md`

## 5.4 验收标准

- 可以明确回答“当前主线默认 baseline 是什么，状态是什么”；
- `LSTM` 与 `XGB` 的比较不再依赖不同时间窗或临时 CLI 覆盖；
- 主线默认报告能稳定输出统一比较结果。

---

## 5A. Phase O1A：股票池模组基线与双窗口协议

## 5A.1 目标

在继续扩大主模型和 `1d` 实验前，先固定股票池与评估窗口的统一 contract。

## 5A.2 必做任务

1. 固定股票池模组位置：`src/ashare_lab/stock_pool/`
2. 固定股票池基线规则：
   - `csi300` 可作为冻结外部基线
   - 其余新增研究池后续优先通过 `stock_pool` 模组推进
3. 建立股票池 registry 基线，优先预留：
   - 单板块池
   - 高相关板块池
   - 反板块池
4. 固定双窗口评估协议：
   - `fixed_20230101_20250701`
   - `latest_rolling`
5. 让主模型与 `1d` 实验卡都显式记录：
   - `stock_pool_id`
   - `evaluation_window_id`

## 5A.3 建议涉及文件

- `docs/modules/stock_pool_module_baseline_20260311.md`
- `docs/modules/stock_pool_registry_baseline_20260311.md`
- `docs/overview/dual_window_evaluation_baseline_20260311.md`
- `docs/research/1d_experiment_protocol.md`
- `docs/branch_tasks/develop.md`
- `docs/branch_tasks/feature_model_d1_research.md`
- `src/ashare_lab/stock_pool/__init__.py`

## 5A.4 验收标准

- 股票池不再只是零散 `symbols_csv`
- `csi300` 与其他研究池的推进方式有明确分界
- 双窗口协议成为后续实验默认前提

---

## 5B. Phase O1B：股票池模组开发立项与第一阶段实现

## 5B.1 目标

把股票池模组从“文档预留”推进到“近期开发中的 dependency 模块”。

## 5B.2 必做任务

1. 明确股票池模组开发计划：
   - `S1 Registry 与基础接口`
   - `S2 首批池子家族支持`
   - `S3 训练/评估链路接线`
   - `S4 smoke test`
2. 把 `S1-S2` 列为近期必须完成项。
3. 让后续主模型和 `1d` 多池扩展显式依赖股票池模组，而不是继续走手工 `symbols_csv`。
4. 在文档中明确：
   - `csi300` 是冻结例外
   - 其他池子统一走 `stock_pool` 模组

## 5B.3 建议涉及文件

- `docs/modules/stock_pool_module_development_plan_20260311.md`
- `docs/modules/stock_pool_module_baseline_20260311.md`
- `docs/modules/stock_pool_registry_baseline_20260311.md`
- `docs/branch_tasks/develop.md`
- `docs/branch_tasks/feature_model_d1_research.md`

## 5B.4 验收标准

- 股票池模组已经进入明确开发排期；
- `S1-S2` 被列为近期依赖项；
- 后续主模型和 `1d` 的扩展计划都已显式依赖该模块

---

## 6. Phase O2：`feature/model-d1-research` 对齐与吸收准备

## 6.1 目标

把 `1d` 分支从“独立研究 worktree”推进到“可控吸收的研究资产包”。

## 6.2 必做任务

1. 先让 `feature/model-d1-research` 对齐当前 `develop`。
2. 人工解决三处已知冲突：
   - `docs/README.md`
   - `docs/research/README.md`
   - `scripts/run_xgboost_rolling_retrain_regime.py`
3. 保留 `1d` 独立研究定位，不让其回写为默认主线。
4. 跑通该分支既有目标测试集。
5. 整理“哪些内容要合并、哪些结论只保留为研究结论”的最终清单。

## 6.3 建议涉及文件

- `docs/research/1d_experiment_protocol.md`
- `docs/research/model_d1_audit_20260309.md`
- `scripts/compare_ic_reports.py`
- `scripts/run_xgboost_rolling_retrain_regime.py`

## 6.4 验收标准

- `1d` 研究协议、命名规则、门禁工具能被 `develop` 吸收；
- 主线默认口径不被 `1d` 倒灌；
- 冲突文件的合并逻辑清晰，可解释，不靠“保留 ours/theirs”硬过。

---

## 7. Phase O3：执行层设计资产规范化吸收

## 7.1 目标

回收 `feature/execution-layer-v2` 的设计成果，但明确它仍不是功能完成分支。

## 7.2 必做任务

1. 盘点执行层文档，区分三类：
   - 应吸收为稳定设计基线
   - 应保留为 working memory
   - 应在实现开始后重写
2. 只吸收稳定设计文档进入 `develop`。
3. 明确后续执行层真实实现的分阶段任务：
   - `PortfolioManager`
   - 回测诊断与日志
   - 固定信号回放验收
4. 为执行层实现预先定义最小测试与验收产物。

## 7.3 建议优先吸收的文档

- `docs/research/execution_layer_branch_plan_20260309.md`
- `docs/technical/execution_layer_phase_implementation.md`
- `docs/technical/portfolio_manager_algorithm.md`
- `docs/technical/phase0_design_research_single_score_input.md`

## 7.4 暂不作为合并目标的内容

- `docs/modules/execution_layer_working_memory.md`

原因：

- 它是过程型工作记忆，不适合作为长期项目基线文档。

## 7.5 验收标准

- `develop` 拥有可执行层的稳定设计文档；
- 后续实现不再依赖旧分支上下文；
- 不出现“文档已合并，所以功能也算完成”的误判。

---

## 8. Phase O4：分支启动与文档流程基线

## 8.1 目标

把这次审计里暴露出来的重复协作成本，变成明确流程。

## 8.2 必做任务

1. 固定分支启动模板，至少包含：
   - 目的
   - In Scope
   - Out of Scope
   - 术语边界
   - source of truth
   - 验收标准
2. 固定默认配置状态模板：
   - `model_track`
   - `config_profile`
   - `config_status`
3. 固定入口文档规则：
   - 入口文档只保留导航
   - 实验细节与复盘下沉到专项文档
4. 固定评估口径规则：
   - 主模型只保留一个主评估口径
   - 旧口径必须降级或退出默认入口
5. 固定提交切分建议：
   - 收口提交
   - 新能力提交
   - 文档同步提交

## 8.3 建议产出

- 新增：`docs/overview/branch_kickoff_baseline_20260311.md`
- 新增：`docs/overview/doc_entry_rules_20260311.md`

## 8.4 验收标准

- 下一条新分支启动时，不再需要重新讨论“计划写哪里、边界怎么定、入口文档怎么改”；
- 配置状态、评估口径、文档职责都有稳定模板；
- 入口页冲突显著下降。

---

## 9. 推荐执行顺序

1. 先做 `Phase O0`，因为这是同步后最直接的工程风险。
2. 再并行推进 `Phase O1` 与 `Phase O2`：
   - `O1` 负责把主模型变成稳定 baseline；
   - `O2` 负责准备下一条研究分支的吸收。
3. 然后做 `Phase O3`，把执行层方案资产纳入主基线。
4. 最后做 `Phase O4`，把这次经验固化成分支启动标准。

---

## 10. 本轮计划的完成定义

以下条件全部满足后，可认为“主模型同步后的整理优化”完成：

1. 测试入口已经统一；
2. 主模型 `LSTM/XGB` baseline 具备可复现、同口径比较能力；
3. `feature/model-d1-research` 已具备可吸收状态；
4. 执行层稳定设计文档已回收进 `develop`；
5. 新分支启动、文档入口、配置状态、评估口径都有统一模板。
