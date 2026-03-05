# IC评估体系最小改造清单与改造计划（V1）

## 1. 目标与边界

### 1.1 目标（只做最小必要改造）
- 目标 1：让标签定义与交易协议严格一致，消除最主要的伪信号来源。
- 目标 2：让评估指标从“单点 IC”升级为“Daily-CS + 稳定性 + 成本后表现”。
- 目标 3：把防伪信号检查固化为门禁，避免回归“指标好看但不可交易”。

### 1.2 非目标（本轮不做）
- 不更换模型架构（如 LSTM 改 Transformer/GNN）。
- 不扩展大规模新因子库。
- 不做分钟级/高频执行改造。

---

## 2. 当前关键错配（必须先修）

1. 交易协议是 `t` 收盘后出信号、`t+1 open` 成交（`docs/protocol.md`）。
2. 多周期标签当前是 `close[t+h]/close[t]-1`（`src/ashare_lab/labels/multi_horizon.py`）。
3. 推荐验证当前也是 `close -> close`（`src/ashare_lab/recommendation/validator.py`）。
4. 训练评估默认把全样本拼接后算 IC，未强制 Daily-CS（`src/ashare_lab/training/mtl_finetune/__init__.py`）。

结论：现在的高 IC 可能混入“不可交易优势”，需要先做交易一致化。

---

## 3. 最小改造清单（Checklist）

## 3.1 M1：标签交易一致化（最高优先）
- [ ] 在 `MultiHorizonLabel` 增加可配置标签口径：
  - `close_to_close`（兼容旧口径）
  - `next_open_to_open`（新默认推荐）
- [ ] 新公式（推荐）：
  - `label_h(t) = open(t+h+1) / open(t+1) - 1`
- [ ] 停牌/缺价有效性掩码同步切换到 `open` 对应窗口。
- [ ] 在数据构建脚本透传参数：
  - `scripts/build_sequence_dataset.py`
  - `scripts/build_sequence_dataset_market_state.py`
- [ ] 在元数据中写入 `label_mode`，便于后续审计。

验收标准：
- 单元测试覆盖 2 种 label_mode，公式校验通过。
- 生成的数据集 metadata 明确记录 label_mode。

## 3.2 M2：验证器与执行口径一致化
- [ ] 推荐验证收益计算改为和执行一致（默认 `next_open_to_open`）。
- [ ] 保留兼容参数（允许 `close_to_close` 仅用于历史对照，不作为主评估）。
- [ ] `ValidationResult` 增加口径字段（如 `return_mode`）。

改造文件：
- `src/ashare_lab/recommendation/validator.py`

验收标准：
- `tests/test_recommendation_validator.py` 增加 open 口径测试并通过。

## 3.3 M3：Daily-CS 成为主指标
- [ ] 在 `evaluation/metrics.py` 增加统一函数：
  - `calculate_daily_cs_ic(...)`
  - `summarize_daily_cs(...)`（mean/std/ICIR/t-stat）
- [ ] 训练/验证报告必须输出 Daily-CS 汇总，不再只给全样本 IC。
- [ ] 对比脚本继续强制 `--daily-cs-mode required`。

改造文件：
- `src/ashare_lab/evaluation/metrics.py`
- `scripts/compare_ic_reports.py`（仅补充字段与校验）
- 训练评估落盘逻辑（对应脚本/模块）

验收标准：
- 报告中同时存在 `daily_cs` 与 `monthly` 统计。
- 缺失 Daily-CS 的报告不能进入 strict 对比。

## 3.4 M4：成本后与风险指标补齐（最小集合）
- [ ] 在回测统计增加：
  - `ann_vol`, `sharpe`, `sortino`, `calmar`
  - `win_rate_daily`, `net_return_after_cost`
- [ ] 输出明确区分 `gross` 与 `net`（至少在统计字段命名上可区分）。

改造文件：
- `src/ashare_lab/backtest/engine.py`
- `scripts/run_backtest.py`（打印字段同步）

验收标准：
- 回测 stats 中可直接读取风险收益指标，不再只看 CAGR/MDD。

## 3.5 M5：防伪信号 Sanity Check 固化
- [ ] 新增统一脚本（或模块）跑 3 个实验：
  - 标签随机化（shuffle labels）
  - 时间反转（time reverse）
  - 全特征滞后 1 天（lag-1）
- [ ] 产出结构化 JSON 报告，可用于门禁。

建议文件：
- `scripts/run_sanity_checks.py`
- `tests/test_sanity_checks.py`（可选，至少保证核心函数可测）

验收标准：
- `shuffle`/`reverse` IC 接近 0（阈值可先设 `|IC| < 0.02`）。
- 任一失败则实验结论标记为“不可信”。

## 3.6 M6：报告协议与门禁固化
- [ ] 每份实验报告新增 `evaluation_protocol` 区块：
  - `signal_time_mode`
  - `execution_time_mode`
  - `label_mode`
  - `cost_model`
  - `daily_cs_mode`
- [ ] 对比脚本在协议不一致时直接拒绝比较。

验收标准：
- 不同 label_mode 报告不可直接混比。

---

## 4. 分阶段改造计划（最小可落地）

## 4.1 Phase A（Day 1）：先修时序一致性
任务：
1. 完成 M1（标签口径改造）。
2. 完成 M2（验证器口径改造）。
3. 补齐测试：`test_labels`、`test_recommendation_validator`。

退出条件：
- 新旧 label_mode 都可跑通。
- 默认流程使用 `next_open_to_open`。

## 4.2 Phase B（Day 2）：统一主评估口径
任务：
1. 完成 M3（Daily-CS 主指标化）。
2. 完成 M6（报告协议字段与强校验）。
3. 更新研究工作流文档（strict 流程）。

退出条件：
- `compare_ic_reports.py --daily-cs-mode required` 可稳定用于所有新报告。
- 报告内包含协议字段与 Daily-CS 统计。

## 4.3 Phase C（Day 3）：补风险和防伪门禁
任务：
1. 完成 M4（成本后风险指标）。
2. 完成 M5（sanity check 自动化）。

退出条件：
- 回测报表可直接看 `net + risk`。
- 每轮实验都自动产出 sanity 报告。

---

## 5. 验收门禁（V1 建议）

## 5.1 协议一致性门
- `signal_time_mode=close`
- `execution_time_mode=next_open`
- `label_mode=next_open_to_open`
- 协议不一致的报告不得参与主结论。

## 5.2 预测质量门（Daily-CS）
- `mean(IC_5_10) >= 0.05`
- `mean(RankIC_5_10) >= 0.08`
- `ICIR_5_10 >= 0.5`（新增）
- 月胜率 `>= 60%`
- 最差月 `>= -0.10`
- 连续负月 `<= 2`

## 5.3 可交易性门（成本后）
- `net_excess_ann > 0`
- `net_sharpe > 0.8`（可先放宽，后续上调）
- `turnover_ratio` 不得异常飙升（与基线相比上限 +30%）

## 5.4 防伪信号门
- shuffle 标签：IC 接近 0
- 时间反转：IC 接近 0
- lag-1：若 IC 大幅崩塌，需要在报告中解释来源

---

## 6. 执行命令模板（按阶段）

## 6.1 测试（建议最小集）
```bash
pytest -q tests/test_labels.py tests/test_recommendation_validator.py tests/test_compare_ic_reports.py
```

## 6.2 覆盖率审计
```bash
python "scripts/audit_ic_reports.py" \
  --reports "output/reports/*.json" \
  --tag 20260305_eval_refactor
```

## 6.3 严格对比（Daily-CS）
```bash
python "scripts/compare_ic_reports.py" \
  --reports "output/reports/a.json" "output/reports/b.json" \
  --metric-source raw \
  --monthly-source raw \
  --daily-cs-mode required \
  --tag 20260305_eval_refactor
```

## 6.4 Sanity Check（新增后）
```bash
python "scripts/run_sanity_checks.py" \
  --report "output/reports/your_experiment.json" \
  --tag 20260305_eval_refactor
```

---

## 7. 回滚与风险控制

- 所有新改造保留兼容开关：`label_mode`、`return_mode`。
- 若 Phase B 期间出现兼容问题，允许临时回退到旧口径仅做“历史复现”，但新实验禁止使用旧口径出主结论。
- 每次改造后先跑最小测试集，再跑一组小样本实验，最后全量回测。

---

## 8. 交付物清单

- 代码：
  - 标签口径与验证器改造
  - Daily-CS 汇总函数
  - 回测风险指标补齐
  - sanity check 脚本
- 文档：
  - 本文档
  - Prompt 包（见《IC评估体系改造Prompt包》）
- 报告：
  - 一份旧口径 vs 新口径的 AB 对照报告
  - 一份带 sanity check 的最终研究报告
