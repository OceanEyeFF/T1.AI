# future_roadmap_suggestions（2026-03-08 更新）

> 目的：基于最近一批提交的**代码实际变更**，重新校准后续路线图，避免“提交信息和真实落地不一致”导致的规划偏差。

说明：当前 `3d/5d/10d` 主模型层的详细执行顺序，已单独整理到 [mainline_3510d_model_development_plan_20260310.md](mainline_3510d_model_development_plan_20260310.md)。本文继续保留项目级研究背景与路线判断，不再承担主模型层的专项执行清单。

---

## 1. 最近提交一致性审计（Commit message ↔ code reality）

审计范围：

- `42cfe9d feat(train): add env guard and config-file driven training runs`
- `44c39b8 feat(tuning): add multilevel tuning runner and dry-run tests`
- `987cfa5 feat(xgb): add auto-tuning script and parser tests`
- `7dbcd3d chore(config): add baseline and fastpilot TOML presets`
- `81e7e15 docs(research): sync roadmap/index and tuning execution guide`
- `f31efed feat(data): add config-driven dataset builders and 1d HLC labels`
- `de28a71 chore(deps): sync optuna and add pip requirements files`
- `0fe4ab8 chore(cleanup): remove stale experiment artifacts`

### 1.1 审计结论（摘要）

- **总体对得上**：大多数提交信息与代码内容一致，属于“描述准确”区间。
- **存在轻微超前预期**：`feat(data)` 已把 `1d HLC` 标签与数据构建能力铺好，但默认研究基线仍是 `3d/5d/10d`，`d1` 尚未进入默认训练主链路。
- **关键缺口未被最近提交覆盖**：执行层（换仓门槛/成本覆盖/策略接线）仍是当前阶段最核心待办。

### 1.2 逐提交核对

1) `feat(train)` —— **匹配度：高**

- 新增了可复用配置装载工具（JSON/TOML、key 校验）。
- 新增 conda 环境守卫，要求脚本在 `ashare-lab` 环境运行。
- 训练脚本显式接入了 `--config-file` / `--effective-config-out` 与 env guard。

2) `feat(tuning)` —— **匹配度：高**

- 脚本明确是多层级调参运行器，支持 L1/L2/L3、LSTM/XGB。
- 测试覆盖了 dry-run 可执行、命令构造与参数过滤。

3) `feat(xgb)` —— **匹配度：中高**

- 存在评分与月度聚合相关的自动调参逻辑单测（说明 parser/score 流程落地）。
- 该提交主题“auto-tuning + parser tests”与代码风格一致。

4) `chore(config)` —— **匹配度：高**

- baseline / fastpilot 配置已新增，且 fastpilot 确实是“低成本试跑”参数（如极低 epoch/patience）。

5) `feat(data)` —— **匹配度：高（但需加注释）**

- 数据构建脚本支持 `--config-file` 与 `--include-1d-hlc-labels`。
- 标签模块新增 `OneDayHLCLabel` 与 `next_open_to_open` 模式，功能落地明确。
- 但研究基线文档仍强调 `1d` 不作为默认头，需要保持“实验态”而非“默认态”管理。

6) `chore(deps)` —— **匹配度：高**

- `optuna` 在 `pyproject.toml` / `requirements*.txt` / `environment.yml` 均出现，依赖同步动作完整。

7) `chore(cleanup)` —— **匹配度：高**

- 研究 README 已声明旧实验入口移除，和清理产物动作方向一致（保持仓库轻量化）。

---

## 2. 现状判断：项目推进“偏模型基础设施”，执行层仍是主风险

### 2.1 已推进（可复现性/效率）

- 配置驱动训练、环境守卫、调参编排、基线 presets 已形成一套“可批量迭代”的研究流水线。

### 2.2 未闭环（可交易性/执行正确性）

- `PortfolioManager` 仍以 TopN 等权为主，换仓阈值与成本覆盖逻辑仍停留在阶段2 TODO 语义。
- 这意味着“模型分数 -> 真实交易动作”的关键层尚未完成，当前回测表现存在执行抽象偏粗的问题。

---

## 3. 更新后的路线：双分支并行 + 明确门禁

> 原则：模型层和执行层解耦推进；默认主干只接收“口径一致 + 门禁通过”的变更。

### 3.1 Branch A（执行层）：`feature/execution-layer-v2`

**目标**：把“可交易决策链”做实。

P0（本周）：

1. 在 `PortfolioManager` 接入换仓门槛：
   - 仅当 `new_score - current_score > rebalance_threshold` 允许替换。
2. 在 `PortfolioManager` 接入成本覆盖：
   - 仅当 `expected_edge > cost_coverage_ratio * expected_cost` 允许换仓。
3. 与 `BacktestEngine` 诊断字段联动：
   - 对“risk gate 禁买、涨跌停阻断、T+1 阻断”做统一统计核对。

P1（下周）：

1. 增加持仓约束（最小持有期/最大持仓数/现金下限）。
2. 标准化输出：策略决策日志 + 交易执行日志 + 诊断摘要。
3. Gate：交易层指标不退化（成本占比、换手、成交阻断解释率）。

### 3.2 Branch B（模型层）：`feature/model-d1-research`

**目标**：继续提升信号质量，但不直接污染默认生产口径。

P0（本周）：

1. 维持默认三头（3d/5d/10d）为主线。
2. `d1` 仅做实验头（不开默认）。
3. 固化对比面板：同 OOS 月份下比较 IC/RankIC/月胜率/最差月/连续负月。

P1（下周）：

1. 在不改变执行层的前提下，比较 XGB vs LSTM vs 轻量融合。
2. 对 `d1` 做“增益是否覆盖噪声/换手放大”的专项审计。
3. Gate：若 `d1` 导致稳定性退化，则继续留在实验分支。

---

## 4. PortfolioManager 何时开始“用真实数据测试”

建议从**阶段化门槛**进入，而不是等所有功能完成：

### 阶段 S0（立即）

- 保持现有单元测试 + 合成样本验证函数行为。

### 阶段 S1（执行层 P0 完成后）

- 上小样本历史窗口（如 6~12 个月）做集成回放：
  - 输入：固定模型分数序列；
  - 输出：目标权重、订单、成交、诊断。
- 目的：验证执行逻辑正确，不验证 alpha。

### 阶段 S2（执行层 P1 + 模型层 P0 完成后）

- 上统一 OOS 时间窗做策略比较：
  - 同一执行层下比较不同模型输出；
  - 同一模型下比较不同执行阈值。
- 目的：拆解“信号问题”与“执行吞噬”各自贡献。

---

## 5. 未来两周产出清单（可验收）

Week 1：

- 执行层：换仓阈值 + 成本覆盖 + 诊断联动 PR。
- 模型层：三头基线与 `d1` 实验头并行面板（同窗口径）。

Week 2：

- 执行层：加入持仓约束与标准化决策日志。
- 模型层：XGB/LSTM/融合对照报告 + `d1` 去留建议。

验收标准：

1. 每个实验必须可重跑（配置文件 + 环境守卫 +输出完整）。
2. 每个策略变更必须解释交易层指标变化来源。
3. 默认主线只接受 Gate=pass 且与接口口径一致的方案。

---

## 6. 关键提醒（避免再踩坑）

- 当前“难点”不在是否有更复杂模型，而在是否把执行层从“示例实现”升级为“可审计实现”。
- `d1` 能力已经具备“数据与标签层可试验”，但距离“默认主线可用”仍有训练/评估/导出链路改造工作。
- 新闻 embedding 属于后置插件，不应阻塞当前执行层主线收敛。
