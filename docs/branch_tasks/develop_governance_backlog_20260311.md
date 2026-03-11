# `develop` 治理总清单（2026-03-11）

## 0. 文档定位

本文档是 `develop` 分支在"项目治理期"的总体工作清单。

**角色：**
- 治理主轴的总索引与跟踪入口
- 跨分支影响分析的统一承载
- 各专题完成后更新分支任务状态的指导依据

**与 `develop.md` 的关系：**
- `develop.md` 记录 develop 分支的全部待办（含研究依赖、模组推进）
- 本文档只聚焦 4 个治理专题，是 `develop.md` 中治理项的细化拆解

---

## 1. 治理总纲

### 1.1 为什么此时做治理

- `feature/model-3d-5d-10d-head` 已同步进 develop，主模型代码基线初步稳定
- 3 条工作分支各自沉淀了大量文档/配置/命名约定，但互不兼容
- 后续无论推进哪条线（主模型 baseline、1d 吸收、执行层实现），都需要先有统一治理基础
- 不先做治理就推进功能，会重复上一轮的分支冲突和协调成本

### 1.2 四项核心治理专题

| 编号 | 专题 | 目标 | 优先级 |
|------|------|------|--------|
| G1 | Merge/Audit Checklist 基线 | 守住 develop 门槛，让分支吸收有标准 | P0 |
| G2 | docs/ 目录治理与归档规则 | 消除文档混乱，固定维护边界 | P0 |
| G3 | 1d / 3d\|5d\|10d 公用层盘点 | 预研共享抽象的边界，防止过早耦合 | P1 |
| G4 | 配置与实验产物命名/版本规范 | 统一 ID 体系和版本语义 | P1 |

### 1.3 治理原则

- 治理不是写方案，是固定规则并立即生效
- 治理产物必须是可执行的 checklist / 规范 / 模板，不是讨论稿
- 每个专题完成后，必须同步更新受影响分支的任务文档
- 治理期间 develop 不承接新的功能实现

---

## 2. 跨分支影响总矩阵

### 2.1 影响方向

```
develop 治理完成
  ├── → feature/model-d1-research    （解锁对齐条件）
  ├── → feature/execution-layer-v2   （解锁规范吸收条件）
  └── → feature/model-3d-5d-10d-head （触发归档状态更新）
```

### 2.2 详细影响映射

| 治理专题 | d1-research 影响 | execution-layer-v2 影响 | 3d-5d-10d-head 影响 |
|----------|------------------|-------------------------|---------------------|
| G1 Merge/Audit | 明确 1d 吸收时必须过哪些门 | 明确执行层文档吸收标准 | 补归档 checklist |
| G2 docs/ 治理 | 冲突文件合并有规则可依 | working memory 归档有标准 | 入口文档不再争抢 |
| G3 公用层盘点 | 明确 1d 哪些代码可复用主线 | 明确执行层接口依赖边界 | 确认已贡献的公用层 |
| G4 配置/版本规范 | stock_pool_id 等 ID 统一 | 实验产物目录规则统一 | 确认已有配置状态 |

### 2.3 各分支待更新任务

治理专题完成后，以下分支任务文档需要同步更新（深入分支核实状态）：

**`feature/model-d1-research`（重点更新）**
- `[ ] 先对齐当前 develop` → 更新为可执行条件（G1 完成后明确 checklist）
- `[ ] 将 1d 股票池使用方式对齐到统一 registry` → 更新 registry 规范引用（G4）
- `[ ] 把 1d 评估对齐到双窗口协议` → 确认协议引用路径（G4）
- 新增：文档冲突合并须遵守的 docs 治理规则（G2）

**`feature/execution-layer-v2`（中等更新）**
- `[ ] 盘点执行层文档，区分稳定/working memory/重写` → 用 G2 规则判定归类
- `[ ] 将稳定设计文档择优吸收到 develop` → 须通过 G1 checklist
- 新增：文档吸收须走的 merge 审核流程（G1）
- 新增：设计文档命名须对齐的规范（G4）

**`feature/model-3d-5d-10d-head`（轻量更新）**
- 确认归档状态标记
- 确认已同步代码在公用层盘点中的位置（G3）
- 确认已有配置的命名是否符合新规范（G4）

---

## 3. 专题 G1：Merge/Audit Checklist 基线

### 3.1 Why

当前分支合入 develop 没有统一标准。上一轮 3d-5d-10d 合并靠"审计文档 + 人工判断"，
没有形成可复用的 checklist。后续 1d 吸收和执行层文档回收会更复杂，没有标准就会重复博弈。

### 3.2 What - 交付产物

- [ ] 新增文档：`docs/overview/merge_audit_checklist_20260311.md`
- [ ] 包含以下 checklist 类型：
  - **代码分支合入 checklist**（适用于有代码改动的分支）
  - **文档/方案分支吸收 checklist**（适用于纯文档分支）
  - **研究分支结论吸收 checklist**（适用于研究成果回收）

### 3.3 Tasks - 可执行子任务

- [x] G1.1 定义"代码分支合入"必须通过的检查项：
  - 时间对齐检查（硬要求）
  - Contract 灵活性检查（允许差异但需标注）
  - 测试入口标准化
  - 文档入口导航化
  - 配置状态显式标注
  - 验收产物齐全
  - 冲突文件分级记录
- [x] G1.2 定义"文档/方案吸收"必须通过的检查项：
  - 稳定文档 vs working memory 是否已区分
  - 文档颗粒度是否符合 `doc_governance.md`
  - 不存在"文档已合并 = 功能已完成"的误判
- [x] G1.3 定义"研究结论吸收"必须通过的检查项：
  - 研究协议是否已卡片化
  - 命名规则是否对齐 registry
  - 门禁规则是否可复用
  - 不存在研究结论回写为默认主线的情况
- [x] G1.4 将 checklist 应用到 `develop.md` 中的现有合入任务描述
- [x] G1.5 更新各分支任务文档，关联 merge_audit_checklist

### 3.4 Done - 验收标准

- [x] 下一次分支合入时，可以逐项对照 checklist 决定是否通过
- [x] checklist 不依赖个人判断，可被不同人（或 AI）一致执行
- [x] `develop.md` 中"从执行层分支吸收稳定设计文档"等任务已关联到 checklist

**完成时间：** 2026-03-11
**产出文档：** [merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md)
**验证方案：** [g1_validation_plan_20260311.md](g1_validation_plan_20260311.md)
**验证完成：** 2026-03-11，发现 5 个问题并全部修正
**验证归档：** `docs/archive/g1_validation_20260311/`
**改进提交：** `79b827f docs(governance): improve merge audit checklist based on G1 validation`

**改进内容：**
1. §3.1 补充 Working Memory 归档流程
2. §3.2.1 新增配置文件检查项
3. §2.4 补充"导航"定义（区分导航内容 vs 长文本描述）
4. §3.4 自查表增加强制变更清单
5. §3.5 新增兜底检查（覆盖所有文件类型）

**状态：✅ G1 已完成并通过验证，Checklist 可正式使用**

### 3.5 跨分支同步动作

完成后须执行：

1. ✅ 更新 `feature_model_d1_research.md`：
   - 在"先对齐当前 develop"下补注："须通过 merge_audit_checklist"
   - 在"整理最终吸收清单"下补注："吸收须逐项通过研究结论 checklist"
2. ✅ 更新 `feature_execution_layer_v2.md`：
   - 在"将稳定设计文档择优吸收到 develop"下补注："须通过文档/方案吸收 checklist"
3. ✅ 更新 `feature_model_3d_5d_10d_head.md`：
   - 补注："已同步分支可参照代码分支 checklist 回顾确认，无需重新执行"

---

## 4. 专题 G2：docs/ 目录治理与归档规则

### 4.1 Why

当前 `docs/` 已有 `doc_governance.md` 定义了颗粒度和命名规则，但存在以下问题：
- 文档是否过期、谁来归档、归档到哪里，没有强制流程
- 分支间入口文档冲突（README.md、NEXT_STEPS.md）反复出现
- 临时审计稿和研究稿堆积，与长期基线文档混杂
- `branch_tasks/` 是新增的分类，但 `doc_governance.md` 还没有覆盖它

### 4.2 What - 交付产物

- [ ] 更新文档：`docs/overview/doc_governance.md`
  - 增加 `branch_tasks/` 的颗粒度规则
  - 增加归档触发条件与归档流程
  - 增加入口文档（README.md 族）的修改权限规则
  - 增加"谁维护、何时归档"矩阵
- [ ] 更新文档：`docs/INVENTORY.md`
  - 补齐当前所有文档的状态标记
- [ ] 可选新增：`docs/overview/doc_lifecycle_rules_20260311.md`
  - 如果 `doc_governance.md` 膨胀过大则拆分

### 4.3 Tasks - 可执行子任务

- [ ] G2.1 盘点当前 docs/ 下所有文档，标记状态：
  - `active`：正在使用的基线文档
  - `frozen`：已冻结、不应修改的快照
  - `stale`：可能过期、需要确认是否归档
  - `archive-candidate`：应移入 archive/
- [ ] G2.2 定义 `branch_tasks/` 的颗粒度规则：
  - 每分支一个文件，不做跨分支合并文档
  - 已归档分支的任务文档保留但标注"已归档"
  - 新分支必须从模板创建任务文档
- [ ] G2.3 定义入口文档修改权限规则：
  - `docs/README.md`：只在 develop 上修改，功能分支不修改
  - `docs/*/README.md`：同层文档变更时同步更新
  - 根目录 `README.md`：只做导航更新，细节下沉
- [ ] G2.4 定义归档流程：
  - 归档触发条件（分支已合并/方案已废弃/结论已提炼）
  - 归档目标位置（`docs/archive/`）
  - 归档动作（移动 + 更新索引 + 留 redirect 说明）
- [ ] G2.5 定义"谁维护、何时归档"矩阵：
  - overview/ → develop 分支维护
  - modules/ → 对应模块所在分支维护
  - research/ → 对应研究分支维护
  - branch_tasks/ → 各分支自维护
  - archive/ → develop 统一管理
- [ ] G2.6 更新 `docs/INVENTORY.md` 补齐状态标记
- [ ] G2.7 清理当前明显过期或重复的文档（如有）

### 4.4 Done - 验收标准

- [ ] 新建文档时，创建者可以快速判断放在哪个目录
- [ ] 入口文档不再是分支合并冲突的高频热点
- [ ] 过期文档有明确的归档路径，不在活跃目录里长期滞留
- [ ] `INVENTORY.md` 是最新的、有状态标记的完整索引

### 4.5 跨分支同步动作

完成后须执行：

1. 到 `feature/model-d1-research` worktree 检查：
   - 其 docs/ 改动是否符合新规则
   - 三处冲突文件（docs/README.md, docs/research/README.md）的合并策略是否可依据新规则确定
2. 到 `feature/execution-layer-v2` worktree 检查：
   - working memory 文档归类是否已按新规则标记
   - 稳定设计文档的归属目录是否正确
3. 确认 `feature/model-3d-5d-10d-head` 的文档产物在 develop 中的状态标记

---

## 5. 专题 G3：1d / 3d|5d|10d 公用层盘点

### 5.1 Why

`1d` 研究线和 `3d/5d/10d` 主线存在代码重叠（特征构建、数据集加载、评估报告、CLI 入口等），
但两条线的 contract 和任务定义不同。如果不先盘点就抽象，容易：
- 把两条任务定义不同的线强行揉成一个中间层
- 抽错层次（先抽了训练流程，但 contract 还没统一）
- 表面复用实际更难维护

所以先做"盘点文档"，不做"抽象实现"。

### 5.2 What - 交付产物

- [ ] 新增文档：`docs/overview/shared_layer_inventory_20260311.md`
- [ ] 包含以下内容：
  - 重复代码点位清单（文件级 + 函数级）
  - 每个重复点的 contract 一致性判断
  - 可抽象层 vs 不可抽象层的分类
  - 推荐抽象优先级

### 5.3 Tasks - 可执行子任务

- [ ] G3.1 列出 1d 和 3d|5d|10d 两条线的代码文件清单
- [ ] G3.2 对每个重复点判断 contract 一致性：
  - 输入 contract 是否相同
  - 输出 contract 是否相同
  - 评估 contract 是否相同
- [ ] G3.3 分类标注：
  - **可立即抽象**：schema、metadata、report loader、config parser
  - **需等 contract 统一后抽象**：数据集构建、实验配置读取
  - **暂不抽象**：训练主流程、模型本体逻辑
  - **不应抽象**：两线本质不同的部分
- [ ] G3.4 对可立即抽象的层，给出推荐的模块位置和接口草案
- [ ] G3.5 明确"公用层抽象的技术门槛"：
  - 两条线必须共享同一个输入 contract
  - 两条线必须共享同一个输出 contract
  - 两条线必须共享同一个评估 contract
  - 只要有一个 contract 不同，就不应强行统一

### 5.4 Done - 验收标准

- [ ] 盘点文档覆盖了 `src/ashare_lab/` 下主要重复代码区域
- [ ] 每个重复点都有 contract 一致性判断，不是简单的"名字一样就统一"
- [ ] 推荐的抽象优先级有明确理由，不是凭感觉排序
- [ ] 明确哪些"不应抽象"，避免后续再反复讨论

### 5.5 跨分支同步动作

完成后须执行：

1. 到 `feature/model-d1-research` worktree 深入检查：
   - 对照盘点结论，确认 1d 代码的 contract 状态
   - 在任务文档中标注"哪些代码后续会被公用层替代"
   - 更新"整理最终吸收清单"中的代码部分
2. 确认 `feature/model-3d-5d-10d-head` 已同步进 develop 的代码：
   - 哪些已是公用层的一部分
   - 哪些仍是 3d|5d|10d 专属

---

## 6. 专题 G4：配置与实验产物命名/版本规范

### 6.1 Why

当前已有多个 ID 体系的基线（stock_pool_id、evaluation_window_id），但缺少：
- configs/ 下配置文件的统一命名和版本规则
- 实验输出目录的统一结构
- dataset_id / experiment_id 的完整定义
- baseline / candidate / frozen 三种状态的统一语义
- 配置文件在分支间的兼容性规则

### 6.2 What - 交付产物

- [ ] 新增文档：`docs/overview/config_and_artifact_naming_20260311.md`
- [ ] 包含以下内容：
  - 配置文件命名规范
  - 实验产物目录结构规范
  - ID 体系完整定义
  - 配置状态语义定义
  - 版本升级规则

### 6.3 Tasks - 可执行子任务

- [ ] G4.1 定义 configs/ 命名规范：
  - 目录结构：`configs/{category}/{name}.toml`
  - 命名规则：`{model_track}_{config_profile}_{version}.toml`
  - 分类：`datasets/`、`experiments/`、`stock_pools/`、`evaluations/`
- [ ] G4.2 定义实验产物目录结构：
  - 输出根目录
  - 子目录命名规则
  - 必须包含的 metadata 文件
- [ ] G4.3 定义完整 ID 体系：
  - `dataset_id`：数据集标识
  - `stock_pool_id`：股票池标识（已有基线）
  - `evaluation_window_id`：评估窗口标识（已有基线）
  - `experiment_id`：实验标识
  - `model_track`：模型线标识
  - `config_profile`：配置档标识
- [ ] G4.4 定义配置状态三分类：
  - `baseline`：当前默认基线，稳定可引用
  - `candidate`：候选配置，正在验证中
  - `frozen`：冻结快照，不再修改
  - 状态流转规则：candidate → baseline（通过门禁）→ frozen（被新 baseline 替代）
- [ ] G4.5 定义版本升级触发条件：
  - 哪些变化必须升版本
  - 哪些变化只需更新 metadata
  - 版本号格式统一
- [ ] G4.6 盘点当前已有配置，标注是否符合新规范
- [ ] G4.7 将已有基线文档（stock_pool_registry、dual_window_evaluation）中的 ID 定义
      与本规范对齐，消除不一致

### 6.4 Done - 验收标准

- [ ] 新建配置文件时，可以快速确定命名、位置和版本号
- [ ] 实验输出有统一目录结构，不同实验的产物可比
- [ ] ID 体系完整且无冲突，已有基线文档与新规范一致
- [ ] baseline / candidate / frozen 三种状态有明确语义，不再靠口头约定

### 6.5 跨分支同步动作

完成后须执行：

1. 到 `feature/model-d1-research` worktree 深入检查：
   - 1d 独立配置（`configs/datasets/1d_independent/`、`configs/experiments/1d_independent/`）
     是否符合新命名规范
   - 1d 实验协议中的 stock_pool_id / evaluation_window_id 引用是否与新规范一致
   - 在任务文档中标注需要调整的配置文件
2. 到 `feature/execution-layer-v2` worktree 检查：
   - 执行层设计文档中引用的配置/产物格式是否与新规范兼容
3. 确认 `feature/model-3d-5d-10d-head` 已有配置在 develop 中的状态标记

---

## 7. 执行顺序与依赖

### 7.1 推荐顺序

```
G1 (Merge/Audit Checklist)
  ↓ 无硬依赖，但为 G2-G4 提供"什么能进 develop"的标准
G2 (docs/ 治理)
  ↓ G2 完成后，文档归类有规则，G3/G4 产出的文档知道放哪里
G3 (公用层盘点)  ←→  G4 (配置/版本规范)
  ↑ G3 和 G4 可并行，但都依赖 G1/G2 先完成
```

### 7.2 最小可行顺序

如果时间紧张，至少先完成：

1. **G1** - 否则后续分支吸收无标准
2. **G4** - 否则后续实验无法统一比较

G2 和 G3 可以稍后补，但不能跳过。

---

## 8. 治理完成定义

以下条件全部满足后，可认为"develop 治理期"核心工作完成：

- [ ] G1：Merge/Audit Checklist 已形成且被后续分支任务引用
- [ ] G2：docs/ 治理规则已更新，INVENTORY.md 已标注状态
- [ ] G3：公用层盘点文档已形成，抽象优先级已明确
- [ ] G4：配置与产物规范已形成，已有基线与新规范已对齐
- [ ] 所有受影响分支的任务文档已同步更新
- [ ] `develop.md` 中的治理相关任务已标记完成或关联到具体产物

---

## 9. 关联文档索引

### 9.1 现有基线文档

- [分支整理与基线对齐审计](../overview/branch_consolidation_audit_20260311.md)
- [主模型同步后优化计划](../overview/post_mainline_sync_optimization_plan_20260311.md)
- [股票池模组基线](../modules/stock_pool_module_baseline_20260311.md)
- [股票池 Registry 基线](../modules/stock_pool_registry_baseline_20260311.md)
- [股票池模组开发计划](../modules/stock_pool_module_development_plan_20260311.md)
- [双窗口评估基线](../overview/dual_window_evaluation_baseline_20260311.md)
- [文档命名与落盘规则](../overview/doc_governance.md)

### 9.2 分支任务文档

- [develop.md](develop.md)
- [feature_model_d1_research.md](feature_model_d1_research.md)
- [feature_execution_layer_v2.md](feature_execution_layer_v2.md)
- [feature_model_3d_5d_10d_head.md](feature_model_3d_5d_10d_head.md)

### 9.3 本次治理将产出的新文档

- `docs/overview/merge_audit_checklist_20260311.md` ← G1
- `docs/overview/config_and_artifact_naming_20260311.md` ← G4
- `docs/overview/shared_layer_inventory_20260311.md` ← G3
- `docs/overview/doc_governance.md`（更新） ← G2
- `docs/INVENTORY.md`（更新） ← G2
