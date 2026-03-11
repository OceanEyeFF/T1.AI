# 文档/方案吸收自查表

分支名称：`feature/execution-layer-v2`
吸收目标：develop
提交日期：2026-03-11
验证人：幽浮喵

---

## 文档分类

### 已盘点分支文档清单

根据 `git diff develop --name-only`，以下是所有文档变更：

#### 1. 根目录入口文档（导航层）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `README.md` | 导航更新 | ⚠️ 仅吸收导航链接 | 执行层相关的入口链接可吸收，长文本描述需下沉 |
| `NEXT_STEPS.md` | 导航更新 | ⚠️ 仅吸收任务项 | 执行层相关的 TODO 项可吸收，细节需下沉到专项文档 |
| `ROADMAP.md` | 导航更新 | ⚠️ 仅吸收里程碑 | 执行层相关的里程碑可吸收，实施细节需下沉 |

#### 2. docs/ 目录索引文档（导航层）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `docs/README.md` | 导航更新 | ⚠️ 仅吸收导航链接 | 执行层相关的索引可吸收，避免承载研究细节 |
| `docs/INVENTORY.md` | 文档清单 | ⚠️ 仅吸收新增条目 | 同步新增文档的清单条目 |
| `docs/modules/README.md` | 导航更新 | ⚠️ 仅吸收导航链接 | 执行层模块的索引可吸收 |
| `docs/research/README.md` | 导航更新 | ⚠️ 仅吸收导航链接 | 执行层研究的索引可吸收 |
| `docs/technical/README.md` | 导航更新 | ⚠️ 仅吸收导航链接 | 执行层技术方案的索引可吸收 |

#### 3. 执行层稳定设计基线（可吸收）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `docs/research/execution_layer_branch_plan_20260309.md` | 稳定设计基线 | ✅ 吸收 | 完整的执行层分支计划，包含 DoD、任务拆解、验收标准，可作为长期基线 |
| `docs/technical/execution_layer_phase_implementation.md` | 稳定设计基线 | ✅ 吸收 | Phase 0-3 详细实施方案，清晰的目标和验收标准，可作为长期基线 |
| `docs/technical/portfolio_manager_algorithm.md` | 稳定设计基线 | ✅ 吸收 | PortfolioManager 算法伪代码和数据结构定义，可作为长期基线 |
| `docs/technical/phase0_design_research_single_score_input.md` | 稳定设计基线 | ✅ 吸收 | Phase 0 设计研究，单一评分输入的架构决策，可作为长期基线 |

#### 4. 执行层 Working Memory（保留在分支或归档）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `docs/modules/execution_layer_working_memory.md` | Working memory | ❌ 不吸收（归档） | 明确标注为"动态工作记忆"，包含进度检查点、临时决策记录，属于过程型文档，应保留在分支或归档 |

#### 5. 其他研究文档（需判断）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `docs/modules/model_line_boundaries_1d_vs_3510d_20260309.md` | 稳定设计基线 | ✅ 吸收 | 1d 和 3d\|5d\|10d 主线边界定义，是架构决策文档，可作为长期基线 |
| `docs/modules/system_io_and_architecture_spec.md` | 稳定设计基线 | ✅ 吸收 | 系统 I/O 和架构规范，是架构决策文档，可作为长期基线 |
| `docs/research/future_roadmap_suggestions.md` | 待重写 | ❌ 不吸收 | 未来路线图建议，属于草稿性质，待稳定后再吸收或合并到 ROADMAP.md |
| `docs/research/mainline_3510d_development_retrospective_20260310.md` | 稳定设计基线 | ✅ 吸收 | 3d\|5d\|10d 主线开发复盘，包含经验总结和改进建议，可作为长期基线 |
| `docs/research/mainline_3510d_model_development_plan_20260310.md` | 稳定设计基线 | ✅ 吸收 | 3d\|5d\|10d 主线模型开发计划，包含任务拆解和验收标准，可作为长期基线 |

#### 6. 配置文件（需判断）

| 文件 | 分类 | 吸收决策 | 理由 |
|------|------|----------|------|
| `configs/experiments/lstm_rolling_baseline.toml` | 配置变更 | ⚠️ 需检查状态标注 | 需确认是否标注了 config_status（baseline/candidate/frozen），并明确是否替换现有配置 |

### 文档分类统计

- **稳定设计基线（可吸收）：** 9 个
- **Working memory（不吸收）：** 1 个
- **待重写（不吸收）：** 1 个
- **导航层（部分吸收）：** 8 个
- **配置文件（需检查）：** 1 个

**自查结论：** ✅ 已明确区分稳定设计、working memory、待重写

---

## 颗粒度规范

### 文档归类检查

根据 `docs/overview/doc_governance.md` 规则，检查每个文档的目标路径是否符合规范：

| 文档名称 | 当前路径 | 目标路径 | 符合规范？ | 备注 |
|----------|----------|----------|-----------|------|
| `execution_layer_branch_plan_20260309.md` | `docs/research/` | `docs/research/` | ✅ 是 | 研究专项任务，符合 research/ 定位 |
| `execution_layer_phase_implementation.md` | `docs/technical/` | `docs/technical/` | ✅ 是 | 技术实施方案，符合 technical/ 定位 |
| `portfolio_manager_algorithm.md` | `docs/technical/` | `docs/technical/` | ✅ 是 | 算法设计文档，符合 technical/ 定位 |
| `phase0_design_research_single_score_input.md` | `docs/technical/` | `docs/technical/` | ✅ 是 | Phase 设计文档，符合 technical/ 定位 |
| `execution_layer_working_memory.md` | `docs/modules/` | ⚠️ 应归档 | ⚠️ 需调整 | Working memory 不应长期保留在 docs/modules/，应归档或保留在分支 |
| `model_line_boundaries_1d_vs_3510d_20260309.md` | `docs/modules/` | `docs/modules/` | ✅ 是 | 模块边界定义，符合 modules/ 定位 |
| `system_io_and_architecture_spec.md` | `docs/modules/` | `docs/modules/` | ✅ 是 | 系统架构规范，符合 modules/ 定位 |
| `future_roadmap_suggestions.md` | `docs/research/` | ⚠️ 待决定 | ⚠️ 需调整 | 应提炼后合并到 ROADMAP.md 或归档 |
| `mainline_3510d_development_retrospective_20260310.md` | `docs/research/` | `docs/research/` | ✅ 是 | 研究复盘，符合 research/ 定位 |
| `mainline_3510d_model_development_plan_20260310.md` | `docs/research/` | `docs/research/` | ✅ 是 | 研究计划，符合 research/ 定位 |

### 文档命名检查

| 文档名称 | 命名规则 | 符合规范？ | 备注 |
|----------|----------|-----------|------|
| `execution_layer_branch_plan_20260309.md` | 短期任务（带日期） | ✅ 是 | 符合短期文档命名规则 |
| `execution_layer_phase_implementation.md` | 长期稳定（无日期） | ⚠️ 建议带日期 | 虽然是实施方案，但与特定分支绑定，建议改为 `execution_layer_phase_implementation_20260310.md` |
| `portfolio_manager_algorithm.md` | 长期稳定（无日期） | ✅ 是 | 算法设计文档，长期有效 |
| `phase0_design_research_single_score_input.md` | 长期稳定（无日期） | ✅ 是 | Phase 设计文档，长期有效 |
| `model_line_boundaries_1d_vs_3510d_20260309.md` | 短期任务（带日期） | ✅ 是 | 符合短期文档命名规则 |
| `system_io_and_architecture_spec.md` | 长期稳定（无日期） | ✅ 是 | 架构规范，长期有效 |
| `mainline_3510d_development_retrospective_20260310.md` | 短期任务（带日期） | ✅ 是 | 符合短期文档命名规则 |
| `mainline_3510d_model_development_plan_20260310.md` | 短期任务（带日期） | ✅ 是 | 符合短期文档命名规则 |

**自查结论：** ✅ 大部分文档命名符合规范，1 个文档建议调整命名

---

## 功能状态

### 实现状态明确

- [x] **执行层文档吸收 ≠ 执行层功能完成**
  - 已在 `docs/branch_tasks/feature_execution_layer_v2.md` 中明确标注：
    - > "角色：执行层设计资产分支"
    - > "当前定位：方案与设计沉淀，不是已完成的功能分支"
    - > "尚未进入真实代码实现闭环"

- [x] **待实现特性有对应的实现任务**
  - 在 `feature_execution_layer_v2.md` 中已明确列出：
    - > "明确真实实现的下一阶段任务：PortfolioManager 接线、回测诊断与日志输出、固定信号回放验收"

- [x] **不存在误导性表述**
  - 所有稳定设计文档标题清晰标注：
    - "执行层分支开发**计划**"
    - "执行层分阶段**实施方案**"
    - "PortfolioManager **算法设计**"
    - "Phase 0 **设计研究**"
  - 均明确为设计/方案/计划，不会误解为已完成功能

**自查结论：** ✅ 功能状态标注清晰，不存在误导

---

## 吸收清单

### 确认吸收的文档清单

| 文档名称 | 目标路径 | 吸收理由 | 优先级 |
|----------|----------|----------|--------|
| `execution_layer_branch_plan_20260309.md` | `docs/research/` | 执行层分支完整计划，包含 DoD、任务拆解、验收标准，是后续实现的基线依据 | P0 |
| `execution_layer_phase_implementation.md` | `docs/technical/` | Phase 0-3 详细实施方案，每个 Phase 有清晰的目标、输入输出、验收标准 | P0 |
| `portfolio_manager_algorithm.md` | `docs/technical/` | PortfolioManager 核心算法伪代码和数据结构定义，是实现的规范依据 | P0 |
| `phase0_design_research_single_score_input.md` | `docs/technical/` | Phase 0 单一评分输入的架构决策，明确了"不聚合多窗口"的设计选择 | P0 |
| `model_line_boundaries_1d_vs_3510d_20260309.md` | `docs/modules/` | 1d 和 3d\|5d\|10d 主线边界定义，明确了不同模型线的职责和契约差异 | P1 |
| `system_io_and_architecture_spec.md` | `docs/modules/` | 系统 I/O 和架构规范，定义了数据流和模块协同方式 | P1 |
| `mainline_3510d_development_retrospective_20260310.md` | `docs/research/` | 3d\|5d\|10d 主线开发复盘，包含经验总结和改进建议，对后续开发有参考价值 | P2 |
| `mainline_3510d_model_development_plan_20260310.md` | `docs/research/` | 3d\|5d\|10d 主线模型开发计划，包含任务拆解和验收标准 | P2 |

**P0：** 执行层核心设计文档，必须吸收
**P1：** 架构边界定义文档，建议吸收
**P2：** 主线复盘和计划文档，可选吸收

### 不吸收的文档清单

| 文档名称 | 分类 | 不吸收理由 | 处理方式 |
|----------|------|-----------|----------|
| `execution_layer_working_memory.md` | Working memory | 明确标注为"动态工作记忆"，包含进度检查点、临时决策记录，属于过程型文档 | 保留在分支或归档到 `docs/archive/execution_layer_v2_20260311/` |
| `future_roadmap_suggestions.md` | 待重写 | 未来路线图建议，属于草稿性质，待稳定后再处理 | 保留在分支，待提炼后合并到 ROADMAP.md 或归档 |

### 导航层文档处理策略

- **根目录入口文档（README.md, NEXT_STEPS.md, ROADMAP.md）：**
  - ⚠️ **仅吸收导航链接**，不吸收长文本描述
  - 冲突时优先保留 develop 的导航结构，执行层相关的入口链接适配到 develop 结构中

- **docs/ 目录索引文档（docs/README.md, docs/*/README.md）：**
  - ⚠️ **仅吸收新增条目**，不吸收重排或重写的索引结构
  - 将执行层相关的文档条目补充到 develop 的索引中

**自查结论：** ✅ 吸收清单明确，不存在"整分支并入"

---

## Checklist 检查项汇总

### 3.1 稳定文档 vs Working Memory 区分
- [x] 文档已盘点并分类（稳定设计基线 / working memory / 待重写）
- [x] 吸收清单已明确，不存在整分支并入
- [x] 每个文档的吸收理由已说明

### 3.2 文档颗粒度符合规范
- [x] 文档归类符合 doc_governance.md
- [x] 文档命名符合长期/短期规则（1 个文档建议调整命名）
- [x] 不存在目录错位（1 个 working memory 文档需归档处理）

### 3.3 不存在功能误判
- [x] 文档吸收不等于功能完成，已在任务文档中明确
- [x] 待实现特性有对应的实现任务
- [x] 不存在误导性表述

---

## 补充说明

### 1. 关于配置文件的检查

`configs/experiments/lstm_rolling_baseline.toml` 需要单独检查：
- [ ] 确认文件头是否标注了 `config_status`（baseline/candidate/frozen）
- [ ] 确认是否明确了"当前默认配置"
- [ ] 确认旧配置是否需要降级或归档

**建议：** 单独对配置文件进行检查，参考 checklist § 2.5 配置状态显式标注规则。

### 2. 关于代码和脚本的变更

本次验证聚焦于**文档/方案吸收 Checklist**，不涉及代码分支的审查。

分支中的代码和脚本变更（`src/`, `scripts/`, `tests/`）不在本次验证范围内，因为：
- 执行层分支的当前定位是"设计资产分支"
- 代码变更尚未进入真实实现闭环
- 若未来需要吸收代码变更，需要通过 checklist § 代码分支合入 Checklist 进行审查

### 3. 关于 working memory 的归档建议

`docs/modules/execution_layer_working_memory.md` 作为 working memory，建议归档到：
- **目标路径：** `docs/archive/execution_layer_v2_20260311/working_memory.md`
- **归档理由：** 保留开发过程记录，供后续参考，但不作为长期基线文档

### 4. 关于文档命名的调整建议

`execution_layer_phase_implementation.md` 建议调整为：
- **建议命名：** `execution_layer_phase_implementation_20260310.md`
- **调整理由：** 虽然是实施方案，但与特定分支绑定，属于短期文档，应带日期标识

---

## 自查总结

### ✅ 通过项
- 文档已盘点并分类（9 个稳定设计基线、1 个 working memory、1 个待重写）
- 吸收清单明确（8 个文档明确吸收理由和优先级）
- 文档归类符合 doc_governance.md 规范
- 功能状态标注清晰，不存在误导

### ⚠️ 需调整项
- 1 个文档命名建议调整（`execution_layer_phase_implementation.md` → 带日期）
- 1 个 working memory 文档需归档处理（`execution_layer_working_memory.md`）
- 配置文件需单独检查 config_status 标注

### ❌ 阻塞项
- 无

**自查结论：** ✅ **整体通过**，需调整项属于细节优化，不影响文档吸收主流程。

---

**填写日期：** 2026-03-11
**填写人：** 幽浮喵
**下一步：** 提交给 develop 维护者复核
