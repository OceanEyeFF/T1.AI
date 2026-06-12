# 下一步工作安排（Next Steps）

**文档颗粒度：** `overview`  
**时间属性：** `current` / `short_term`  
**作用：** 当前阶段执行入口，回答“接下来先做什么、为什么先做、什么算完成”。
**配套导航：** `docs/overview/README.md`

## 当前阶段判断（2026-06-09）

当前文档与代码已经把项目收敛为三个开发方向：

1. **`3d/5d/10d` 短期预测模型线**
   - 这是当前默认主 alpha 线；
   - 默认输出继续围绕 `pred_3d/pred_5d/pred_10d -> alpha_score`；
   - 当前不能默认视为可用交易信号；
   - 近期重点是可信评估范式、伪信号排查、LSTM / XGBoost 同窗比较和优化闭环。

2. **`1d` 超快速预测线**
   - `1d` 不进入默认主线打分；
   - 仅靠日 K 线不足以支撑高质量超短预测；
   - 下一步不是先堆模型，而是先验证日内 / 分钟级数据的可得性、历史长度、字段质量和复现成本。

3. **决策模型线**
   - 负责把预测分数、持仓、成本、风险与交易约束转成可审计动作；
   - 近期只冻结输入 / 输出协议草案；
   - 在主线 `alpha_score` 通过可信评估门禁前，不推进复杂交易决策实现。

相关文档：

- 模型边界：[docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md](docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md)
- 三线开发规划：[docs/overview/three_track_development_plan_20260609.md](docs/overview/three_track_development_plan_20260609.md)
- 主模型层专项计划：[docs/research/mainline_3510d_model_development_plan_20260310.md](docs/research/mainline_3510d_model_development_plan_20260310.md)
- `1d` 执行策略：[docs/research/1d_independent_model_execution_strategy_20260309.md](docs/research/1d_independent_model_execution_strategy_20260309.md)
- 研究路线建议：[docs/research/future_roadmap_suggestions.md](docs/research/future_roadmap_suggestions.md)

## 工作线 A：`3d/5d/10d` 短期预测模型

**目标：** 稳定当前主 alpha 研究线，形成可复跑、可比较、可接入决策模型的预测输出。

详细执行顺序见：[docs/research/mainline_3510d_model_development_plan_20260310.md](docs/research/mainline_3510d_model_development_plan_20260310.md)

### P0：本阶段必须完成

- 固化可信评估范式：
  - Daily-CS IC / RankIC；
  - 月度分布、最差月、连续负月；
  - trade-like Top-N 面板；
  - raw / calibrated / trade-like 的主次关系；
  - 双窗口、近期窗口和压力窗口。
- 系统排查伪信号：
  - 标签成熟日；
  - 交易时点对齐；
  - shuffle / time reverse / lag-1；
  - 复权、停牌、涨跌停和缺失处理；
  - 调参是否过拟合测试集。
- 冻结主线默认配置、默认评估窗口和默认比较指标；
- 固化 `pred_3d/pred_5d/pred_10d -> alpha_score` 的默认聚合契约与导出字段；
- 补齐 LSTM / XGBoost 同窗比较面板：
  - IC / RankIC
  - 月胜率
  - 最差月
  - 连续负月
  - trade-like Top-N 表现
- 保持主线配置、主线门禁、主线报告与 `1d` 旁路线分开。

### P1：P0 完成后推进

- 深化模型优化策略：
  - 窗口长度；
  - 重训频率；
  - loss 权重；
  - rank-aware / IC-aware loss；
  - 特征组增量与消融；
- 在可信评估通过后，再深化 `alpha_score` 校准策略；
- 标准化聚合版本、三头贡献和推荐导出协议；
- 为决策模型提供稳定输入契约。

### 主线验收标准（DoD）

- 任一主线实验都能明确回答“同一时间窗、同一评估口径下是否优于基线”；
- 主线推荐输出默认可回溯到 `3d/5d/10d` 三头贡献；
- 主线报告不混入 `1d` 独立实验指标；
- 高 IC / 高胜率结果能通过防伪检查；
- 通过门禁前，`alpha_score` 只能作为候选研究信号，不能作为默认可交易信号。

## 工作线 B：`1d` 超快速预测与日内数据

**目标：** 单独回答 `1d` 是否值得作为超短周期预测线存在。

### 当前规则

- `1d` 不进入默认主线打分；
- `1d` 不改写主线损失、主线默认配置、主线默认报告；
- `1d` 报告与产物必须独立归档；
- 日 K-only 结果只能作为负对照或最低基线，不作为超快速预测成败的最终判断。

### 近期任务

- 先做日内 / 分钟级数据可用性验证：
  - TuShare `stk_mins` 权限、覆盖、历史长度、拉取速度；
  - AkShare 分钟接口 smoke test 和近期数据字段验证；
  - 复权、停牌、涨跌停、集合竞价、午休断点处理方案；
  - 缓存与增量更新策略。
- 数据验证通过后，再定义 `1d` 标签和分钟特征协议；
- 模型顺序仍为：
  1. `XGBoost + 1d direction`
  2. `LSTM + 1d direction`
  3. `Transformer + 1d direction`（后置）

### `1d` 验收标准（DoD）

- 至少一个分钟级数据源能支撑固定股票池、固定时间窗回放；
- 能独立产出 go / no-go 判断；
- 能说明增益是否覆盖噪声、换手和成本；
- 任何结论都不以“顺手并入主线”作为默认落地方式。

## 工作线 C：决策模型

**目标：** 把“有模型分数”升级为“有可审计的交易决策链”。

### P0：本阶段必须完成

- 冻结决策模型输入 / 输出协议草案；
- 明确当前决策模型依赖主线预测可信门禁；
- 在主线预测未通过门禁前，不把以下规则实现视为第一优先级。

### P1：主线预测通过门禁后推进

- 在 `PortfolioManager` 或对应决策层接入换仓门槛：
  - 仅当新候选相对当前持仓具有足够优势时才换仓；
  - 避免“每天评估 = 每天频繁调仓”。
- 在执行逻辑中接入成本覆盖判断：
  - 仅当预期边际收益能够覆盖预期成本时才允许动作；
  - 避免微弱分数优势被摩擦成本吞噬。
- 与 `BacktestEngine` 诊断字段联动：
  - 明确记录 `risk_buy_disabled`；
  - 区分涨跌停阻断、`T+1` 阻断与风险禁买。
- 标准化输出策略决策日志与交易执行日志：
  - 让回测结果能解释“为什么买、为什么没买、为什么没卖掉”。

### P2：P1 完成后推进

- 增加最小持有期、最大持仓数、现金下限等持仓约束；
- 标准化回测摘要中的换手、成本占比、成交阻断解释率；
- 在固定历史窗口上做决策层集成回放，验证决策逻辑而非验证 alpha。

### 决策模型验收标准（DoD）

- 默认回测链路能输出明确的换仓触发原因；
- 低换手约束后，换手与成本占比不恶化到不可接受区间；
- 成交失败原因能被结构化统计，而不是只体现在净值结果上；
- 同一组固定模型分数输入下，决策输出可复跑、可解释。

## 本周优先级

1. **建立主线 `3d/5d/10d` 可信评估范式**
2. **系统排查伪信号与评估偏差**
3. **补齐 LSTM / XGBoost 同窗比较与优化实验队列**
4. **冻结决策模型 I/O 草案**
5. **启动 `1d` 分钟级数据可用性验证**

## 当前明确不做

- 不把 `1d` 直接合并进主线多头结构；
- 不用日 K-only 结果给 `1d` 超快速预测下最终结论；
- 不在 `3d/5d/10d` 未通过可信门禁前，把决策模型实现当作第一优先级；
- 不在决策模型规则基线未完成前上复杂 policy / RL；
- 不让新闻 / 公告 / 事件 embedding 阻塞当前决策模型闭环；
- 不在入口文档继续维护已经失效的旧阶段任务树。

## 关联文档

- 长期路线：[ROADMAP.md](ROADMAP.md)
- 文档总导航：[docs/README.md](docs/README.md)
- 三线开发规划：[docs/overview/three_track_development_plan_20260609.md](docs/overview/three_track_development_plan_20260609.md)
- 模型线边界：[docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md](docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md)
- `1d` 独立执行策略：[docs/research/1d_independent_model_execution_strategy_20260309.md](docs/research/1d_independent_model_execution_strategy_20260309.md)
- 当前研究路线建议：[docs/research/future_roadmap_suggestions.md](docs/research/future_roadmap_suggestions.md)
