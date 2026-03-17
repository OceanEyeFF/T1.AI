# 股票池模组开发计划（2026-03-11）

## 1. 目的

本文档用于把股票池模组从“基线预留”推进到“正式开发排期”。

当前判断很明确：

- 股票池模组不是锦上添花，而是后续主模型、`1d` 研究和多股票池比较实验的 dependency；
- 若不先落地股票池模组，后续会继续依赖零散 `symbols_csv`、临时命名和手工文档，导致实验不可比；
- 因此股票池模组应进入近期开发排期，而不是继续停留在概念阶段。

---

## 2. 与现有文档的关系

- 模组基线：
  - [stock_pool_module_baseline_20260311.md](stock_pool_module_baseline_20260311.md)
- Registry 基线：
  - [stock_pool_registry_baseline_20260311.md](stock_pool_registry_baseline_20260311.md)
- 双窗口评估基线：
  - [../overview/dual_window_evaluation_baseline_20260311.md](../overview/dual_window_evaluation_baseline_20260311.md)
- 方法论文档：
  - [../research/选股池方法论.md](../research/选股池方法论.md)

本文档回答的是：

- 先做哪些能力；
- 哪些能力暂时不做；
- 做到什么程度才算足以支撑后续工作。

---

## 3. 当前定位

股票池模组放置位置固定为：

`src/ashare_lab/stock_pool/`

模块职责固定为：

1. 股票池 registry；
2. 股票池构建与导出；
3. 股票池元数据与版本；
4. 为训练/评估链路提供统一 `stock_pool_id` contract。

明确不属于本模块的职责：

- 模型训练；
- 个股最终评分；
- 行业链条 ranking；
- 执行层调仓逻辑。

---

## 4. 为什么现在必须做

当前后续工作里，至少有 4 类任务依赖股票池模组：

1. 主模型从单池 baseline 扩展到多池比较；
2. `1d` 研究从单一小池实验扩展到多股票池矩阵；
3. 双窗口评估协议需要和 `stock_pool_id` 共同形成实验 contract；
4. 后续行业/相关板块/反板块研究需要统一 registry 和导出方式。

所以股票池模组应视为：

- `develop` 近期排期中的上游依赖；
- `1d` 研究线后续扩展的前置条件；
- 主模型 baseline 扩展前的基础设施工作。

---

## 5. 分阶段开发计划

## 5.1 Phase S0：基线冻结（已完成）

已完成：

- [x] 模组位置预留：`src/ashare_lab/stock_pool/`
- [x] 模组职责冻结
- [x] `csi300` 例外规则冻结
- [x] registry 基线文档冻结
- [x] 双窗口评估基线文档冻结

本阶段产物：

- [stock_pool_module_baseline_20260311.md](stock_pool_module_baseline_20260311.md)
- [stock_pool_registry_baseline_20260311.md](stock_pool_registry_baseline_20260311.md)
- [../overview/dual_window_evaluation_baseline_20260311.md](../overview/dual_window_evaluation_baseline_20260311.md)

## 5.2 Phase S1：Registry 与基础接口（必须优先实现）

### 目标

让股票池不再只是 `symbols_csv`，而是可注册、可查询、可导出的正式实体。

### 必做任务

1. 定义股票池 registry 数据结构：
   - `stock_pool_id`
   - `stock_pool_version`
   - `pool_family`
   - `construction_method`
   - `base_universe`
   - `rebalance_frequency`
2. 在代码中实现最小 registry 读取与校验入口。
3. 规划 registry 配置目录：
   - 建议：`configs/stock_pools/`
4. 规划导出产物格式：
   - `symbols_csv`
   - `metadata_json`
5. 让训练/评估链路可以开始消费 `stock_pool_id` 和 `stock_pool_version`。

### 建议涉及文件

- `src/ashare_lab/stock_pool/__init__.py`
- 新增：`src/ashare_lab/stock_pool/types.py`
- 新增：`src/ashare_lab/stock_pool/registry.py`
- 新增：`configs/stock_pools/`

### 验收标准

- 至少能注册并加载一个冻结股票池；
- 至少能输出 `symbols_csv + metadata_json`；
- 股票池 ID 与版本可以进入实验元数据。

## 5.3 Phase S2：首批池子家族支持（必须）

### 目标

支撑后续多池研究的第一轮可用池子，而不是一开始做成大而全系统。

### 必做任务

1. 支持 `sector_single_*`
2. 支持 `sector_corr_*`
3. 支持 `sector_anti_corr_*`
4. 明确 `custom_*` 的最小准入规则
5. 保持 `csi300` 作为外部冻结 anchor pool

### 验收标准

- 至少每个家族能落 1 个样例池；
- 样例池具有稳定 ID、版本和导出产物；
- 相关实验可通过 `stock_pool_id` 直接引用这些池子。

## 5.4 Phase S3：训练/评估链路接线（必须）

### 目标

让股票池 registry 真正进入主模型与 `1d` 实验流程，而不是只停留在模块内部。

### 必做任务

1. 在实验卡与配置中加入：
   - `stock_pool_id`
   - `stock_pool_version`
2. 在报告中加入：
   - `stock_pool_id`
   - `stock_pool_version`
   - `evaluation_window_id`
3. 在数据构建脚本中支持由 `stock_pool_id` 驱动选股。
4. 在比较脚本中显式输出当前股票池上下文。

### 建议涉及文件

- `docs/research/1d_experiment_protocol.md`
- `scripts/compare_ic_reports.py`
- 相关 dataset builder / training scripts

### 验收标准

- 不再需要靠文档手工说明“这次用的是哪份股票池”；
- fixed / latest 双窗口比较时，股票池上下文可追溯；
- 主模型和 `1d` 的实验结果可以在同一 contract 下比较。

## 5.5 Phase S4：验证与 smoke test（必须）

### 目标

避免股票池模组引入后，结果仍然不可复现或不可审计。

### 必做任务

1. 增加股票池 registry 读取测试；
2. 增加导出产物测试；
3. 增加错误配置校验测试；
4. 增加一个最小 smoke test：
   - 读取股票池
   - 导出成员
   - 生成 metadata

### 验收标准

- 股票池模块可独立 smoke test；
- 非法 registry 记录能在早期失败；
- 产物可重复导出。

---

## 6. 当前明确不做

- 不在第一阶段直接做行业链条知识图谱；
- 不把个股评分 engine 并入股票池模块；
- 不把选股池模组和模型输出 contract 混成一个层；
- 不先做大规模池子矩阵，再补 registry。

---

## 7. 推荐排期顺序

当前推荐顺序：

1. `S1 Registry 与基础接口`
2. `S2 首批池子家族支持`
3. `S3 训练/评估链路接线`
4. `S4 验证与 smoke test`

理由：

- 如果没有 `S1`，后面所有池子都是临时资产；
- 如果没有 `S3`，模块存在但实验链路仍不会真正使用它；
- 如果没有 `S4`，模块会变成新的不稳定点。

---

## 8. 完成定义

股票池模组进入“可用状态”，至少要满足：

1. 股票池可以注册并版本化；
2. 至少支持 3 类非 `csi300` 池子家族中的样例池；
3. 主模型或 `1d` 至少有一条链路开始直接消费 `stock_pool_id`；
4. 双窗口评估报告可显式记录股票池上下文；
5. 模块具备独立 smoke test。
