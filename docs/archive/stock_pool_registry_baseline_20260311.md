# 股票池 Registry 基线（2026-03-11）

## 1. 目的

本文档用于定义股票池 registry 的最小基线，解决以下问题：

- `1d` 研究线与 `3d/5d/10d` 主线对股票池的命名和记录方式不统一；
- 当前大量实验仍依赖 `symbols_csv` 和文档描述，缺少机器可消费的 registry；
- 后续将引入多套股票池组合，若没有 registry，会迅速失去可比性。

本文档与 [stock_pool_module_baseline_20260311.md](stock_pool_module_baseline_20260311.md) 的关系是：

- 模组基线文档回答“股票池模组放在哪里、负责什么”；
- 本文档回答“registry 至少要登记什么、怎么命名、怎么版本化”。

---

## 2. 结论

后续所有股票池都应具备统一 registry 记录，最少包含：

- `stock_pool_id`
- `stock_pool_version`
- `pool_family`
- `construction_method`
- `base_universe`
- `symbols_source`
- `rebalance_frequency`
- `is_default`
- `is_research_only`

当前例外规则：

- `csi300` 可先作为冻结外部基线池存在；
- 除 `csi300` 外，后续新增池子原则上都应经由 `stock_pool` 模组注册。

---

## 3. Registry 的角色

股票池 registry 不负责：

- 训练模型；
- 直接给模型打分；
- 承担行业链条 ranking 逻辑。

股票池 registry 只负责：

1. 给每个股票池一个稳定 ID；
2. 固定构造方法和版本；
3. 让实验卡、配置、报告都能引用同一只池子；
4. 支撑“同池同窗同口径”比较。

---

## 4. 命名规则

## 4.1 `stock_pool_id`

`stock_pool_id` 必须是稳定 ID，不允许口语化描述。

当前冻结的 ID 家族：

- `csi300`
- `sector_single_*`
- `sector_corr_*`
- `sector_anti_corr_*`
- `custom_*`

禁止再使用下列表达作为正式 ID：

- “默认池”
- “原始池”
- “大盘池”
- “核心池”
- “板块池”

这些叫法只能出现在说明文字里，不能出现在实验元数据里。

## 4.2 `stock_pool_version`

每个股票池都必须带版本号，例如：

- `v1`
- `v2`
- `20260311_v1`

如果以下任一项变化，必须升版本：

- 成分股筛选条件变化；
- 基础宇宙变化；
- 行业/主题映射规则变化；
- 数据源或更新频率变化；
- 去极值 / 剔除规则变化。

---

## 5. Registry 必填字段

每个股票池 registry 记录至少需要：

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

若是行业/主题相关池，额外建议：

- `theme_or_sector`
- `sector_level`
- `correlation_anchor`
- `selection_window`
- `exclusion_rules`

---

## 6. 当前冻结的池子家族

## 6.1 `csi300`

- 定位：冻结的大盘基线池
- 角色：主模型与 `1d` 研究的共同 anchor pool
- 当前规则：
  - 可暂时不走股票池模组内部实现；
  - 但实验仍必须显式记录 `stock_pool_id=csi300`。

## 6.2 `sector_single_*`

- 定位：单板块/单行业池
- 用途：验证特定板块内的模型表现和池内排序能力

## 6.3 `sector_corr_*`

- 定位：高相关板块联动池
- 用途：验证相关产业链/联动结构下的研究表现

## 6.4 `sector_anti_corr_*`

- 定位：反板块/对冲视角池
- 用途：验证不同主题或负相关结构下的区分能力

## 6.5 `custom_*`

- 定位：实验型池
- 规则：
  - 必须写清构造逻辑；
  - 必须明确 `is_research_only=true`；
  - 未通过验证前不得宣称为默认池。

---

## 7. Registry 与实验协议的接线要求

后续所有主线与 `1d` 实验，最少应同时记录：

- `stock_pool_id`
- `stock_pool_version`
- `dataset_id`
- `feature_group_id`
- `label_definition`
- `evaluation_window_id`

这意味着：

- 同一模型若更换股票池，即使其他参数不变，也视为新实验；
- 同一股票池若升版本，即使 ID 不变，也不能直接与旧结果混比。

---

## 8. 建议的落地产物

股票池 registry 后续建议至少形成两类产物：

1. registry 记录
   - 可放在 `configs/stock_pools/` 或等价目录
   - 作为声明式配置
2. 导出产物
   - `symbols_csv`
   - `metadata_json`

其中 `metadata_json` 至少应包含：

- `stock_pool_id`
- `stock_pool_version`
- `generated_at`
- `symbols_count`
- `construction_method`

---

## 9. 第一阶段不做什么

- 不在这一轮直接定义完整行业链条知识图谱；
- 不把个股评分逻辑塞进 registry；
- 不为了“先统一”而一次性铺开太多股票池；
- 不让不同分支继续手工发明新的池子命名体系。

---

## 10. 下一步建议

1. 后续补一个 registry 实体样例，先覆盖：
   - `csi300`
   - 一个 `sector_single_*`
   - 一个 `sector_corr_*`
   - 一个 `sector_anti_corr_*`
2. 把 `1d` 实验协议中的股票池部分升级为引用 registry；
3. 让主模型线的 baseline 也开始显式记录 `stock_pool_id` 与 `stock_pool_version`。
