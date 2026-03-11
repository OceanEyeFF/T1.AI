# Develop 分支合入审核 Checklist（2026-03-11）

## 0. 文档定位

本文档是 `develop` 分支接收其他分支合入时的统一审核标准。

**执行原则：**
- **双重验证**：功能分支提交前自查并填写 checklist → develop 维护者审查时复核
- **门禁性质**：不通过可以打回或协助修正，不能降低标准强行通过
- **可执行性**：每个检查项都有明确判断标准，不依赖主观判断

**与 G4 的关系：**
- 当前版本为"简化版"，使用已有基线文档作为标准
- G4（配置与产物规范）完成后，将更新配置相关检查项的引用规范

---

## 1. 三类分支的 Checklist 分类

根据分支性质，分为三类不同的合入审核流程：

| 分支类型 | 适用场景 | Checklist 类型 |
|----------|----------|----------------|
| **代码分支** | 有代码改动、配置变更、测试新增 | § 代码分支合入 Checklist |
| **文档/方案分支** | 纯设计文档、方案沉淀、working memory | § 文档/方案吸收 Checklist |
| **研究结论分支** | 实验协议、门禁工具、研究成果回收 | § 研究结论吸收 Checklist |

**判断依据：**
- 若分支包含 `src/`、`configs/`、`tests/` 下的代码变更 → 代码分支
- 若分支仅包含 `docs/` 下的文档 → 文档/方案分支
- 若分支主要产出为实验协议、比较工具、门禁脚本 → 研究结论分支

---

## 2. § 代码分支合入 Checklist

**适用示例：**
- `feature/model-3d-5d-10d-head` ✅（已完成，可作为回顾验证）
- `feature/model-d1-research` 🔜（下一个）

### 2.1 时间对齐检查（硬要求）

**原则：** 不同任务定义的模型可以有不同的数据 dim 和输出 contract，但时间边界必须对齐。

```markdown
- [ ] 时间索引对齐
  - DataFrame 索引类型为 datetime64[ns]，升序
  - 训练/验证/测试窗口的日期边界与 develop 已有窗口定义一致
  - 若引入新窗口定义，已在 evaluation_window 基线中注册

- [ ] 评估窗口对齐（当前基线）
  - 若参与 baseline 比较，必须使用 fixed_20230101_20250701 和 latest_rolling
  - 详见：docs/overview/dual_window_evaluation_baseline_20260311.md
```

**自查方式：**
- 读取数据后检查 `df.index.dtype` 和 `df.index.is_monotonic_increasing`
- 对比实验配置中的 `train_window_weeks / valid_window_weeks / test_window_weeks` 与主线是否一致

**审查方式：**
- 查看分支的实验配置 TOML 文件
- 确认报告中的 `evaluation_window_id` 字段

---

### 2.2 Contract 灵活性检查（允许差异）

**原则：** 1d 和 3d|5d|10d 因任务定义不同，允许数据特征维度和输出字段不同，但必须显式标注。

```markdown
- [ ] 输入数据 contract
  - 若任务定义与主线不同，已在分支文档中显式说明差异
  - 新增特征维度已记录在实验协议或数据集文档中
  - 不存在"悄悄换数据源但不说明"的情况

- [ ] 输出 contract
  - 若输出字段与主线不同（如 pred_1d vs alpha_score），已显式版本化
  - 输出 schema 已在代码或文档中定义
  - 不存在"同名不同义"的情况（如都叫 alpha_score 但计算方式不同）
```

**自查方式：**
- 在分支的研究文档或实验协议中补充"数据 contract"和"输出 contract"小节
- 对比主线 `data_contract.md`，标注差异点

**审查方式：**
- 查看分支的 `docs/research/` 下是否有 contract 说明
- 确认代码中的输出字段名与主线是否冲突

---

### 2.3 测试入口标准化

**原则：** 新增测试可通过统一命令运行，核心变更必须有测试覆盖。

```markdown
- [ ] 测试可运行
  - 新增测试可通过统一命令运行（当前标准：PYTHONPATH=src:. pytest -q ...）
  - 测试文件已放在 tests/ 下，遵循命名规则 test_*.py

- [ ] 核心覆盖
  - 核心变更（新模块、新算法、新 schema）已有配套测试
  - 不强制 100% 覆盖，但主流程必须有 smoke test

- [ ] Smoke test 更新
  - 若引入新模块，已更新或确认 smoke test 清单
  - 已知失败的测试（如网络依赖）已在文档中说明
```

**自查方式：**
- 在分支根目录运行 `PYTHONPATH=src:. pytest -q tests/test_{new_module}.py`
- 确认核心变更的代码路径被测试覆盖

**审查方式：**
- 查看 `tests/` 下是否有新增测试文件
- 运行 smoke test 清单，确认不引入新的失败

---

### 2.4 文档入口导航化

**原则：** 入口文档只做导航层更新，细节下沉到专项文档。

**"导航"的定义：**

- **导航内容（可吸收）：**
  - 链接：指向其他文档的超链接
  - 索引：文档清单、目录、章节标题
  - 简短描述：1-2 句话的文档摘要（≤50 字）

- **长文本描述（不可吸收）：**
  - 实验细节：数据集、特征、参数、结果
  - 方案论述：架构设计、算法描述、技术决策
  - 代码示例：伪代码、配置示例
  - 复盘经验：问题分析、改进建议

**判断标准：**
- 若删除后，不影响文档的"可发现性" → 长文本描述（应下沉到专项文档）
- 若删除后，用户无法找到相关文档 → 导航内容（可保留在入口文档）

```markdown
- [ ] 根目录入口（README.md、NEXT_STEPS.md、ROADMAP.md）
  - 变更仅限导航更新，不承载实验细节
  - 若有冲突，优先保留 develop 的导航结构，功能分支适配

- [ ] docs/ 入口（docs/README.md、docs/*/README.md）
  - 已遵守 doc_governance.md 规则
  - 不存在"入口文档承载研究细节"的情况

- [ ] 专项文档下沉
  - 实验细节、复盘经验已下沉到 docs/research/ 或 docs/modules/
  - 新增专项文档已在对应 README.md 中索引
```

**自查方式：**
- 对比分支和 develop 的入口文档差异
- 确认新增内容是"导航链接"而非"长文本描述"

**审查方式：**
- 查看冲突文件（如 docs/README.md）的 diff
- 确认合并策略符合"导航优先"原则

---

### 2.5 配置状态显式标注（简化版）

**原则：** 新增配置必须标注状态，不能让用户猜"哪个是默认"。

```markdown
- [ ] 配置文件状态标注
  - 新增配置已在文件头或 metadata 中标注 config_status
  - 状态分类（当前简化版）：
    - baseline：当前默认基线
    - candidate：候选配置，正在验证中
    - frozen：冻结快照，不再修改

- [ ] 默认入口明确
  - 已明确哪个配置是默认入口（在文档或脚本注释中说明）
  - 旧配置若被替代，已标记降级或移入 archive/
```

**自查方式：**
- 在配置文件开头添加注释块：
  ```toml
  # Config Status: baseline | candidate | frozen
  # Description: 主模型 LSTM 滚动训练基线配置
  # Last Updated: 2026-03-11
  ```

**审查方式：**
- 查看 `configs/` 下新增/修改的文件
- 确认文档或代码中有"当前使用哪个配置"的说明

**注：** G4 完成后，此检查项将升级为引用统一配置规范。

---

### 2.6 验收产物齐全

**原则：** 代码变更必须有对应的文档和示例。

```markdown
- [ ] 文档同步
  - 架构变更有对应的模块文档或 overview 文档
  - 不强制要求 API 文档，但核心抽象必须有说明

- [ ] 配置示例
  - 新增模块有 baseline 配置或 example 配置
  - 配置参数的含义和默认值已说明

- [ ] 依赖说明
  - 若引入新依赖，已更新 pyproject.toml
  - 在 commit message 或文档中说明依赖的作用和必要性
```

**自查方式：**
- 检查 `docs/modules/` 或 `docs/research/` 下是否有对应文档
- 确认 `configs/` 下有可运行的示例配置

**审查方式：**
- 查看分支的文档产出列表
- 尝试运行示例配置，确认能跑通

---

### 2.7 冲突文件分级记录

**原则：** 简单冲突用 commit message 说明，复杂冲突用 PR/审计文档详细说明。

```markdown
- [ ] 冲突文件已人工合并
  - 不是 git merge -X ours/theirs 硬选
  - 已逐段审查冲突内容

- [ ] 合并逻辑有记录
  - 简单冲突（导航顺序、文档描述）：commit message 说明即可
  - 复杂冲突（代码逻辑、协议变更）：必须在 PR 描述或审计文档中详细说明
    - 为什么选择这种合并方式
    - 两边冲突的语义是什么
    - 合并后的行为与预期是否一致
```

**简单冲突示例（commit message）：**
```
merge: resolve docs/README.md navigation conflict

- 保留 develop 的导航结构
- 将 1d 研究入口补充到"研究分支"章节
- 两边的描述文字取并集
```

**复杂冲突示例（需详细文档）：**
```markdown
## 冲突文件：scripts/run_xgboost_rolling_retrain_regime.py

### 冲突原因
- 3d|5d|10d 分支引入主线 schema 聚合相关约束
- 1d 分支增强 horizon 配置与比较口径

### 合并策略
- 保留两边的 horizon 处理逻辑，用 if model_track 区分
- schema 聚合约束只在 3d|5d|10d 模式下生效
- 比较口径工具提升为公用函数

### 验证方式
- 跑通 3d|5d|10d 主线实验
- 跑通 1d 独立实验
- 确认两者不互相干扰
```

**自查方式：**
- 列出所有冲突文件清单
- 对每个冲突文件判断"简单 vs 复杂"
- 准备对应级别的记录

**审查方式：**
- 查看 merge commit message 或 PR 描述
- 确认复杂冲突有详细说明

---

### 2.8 代码分支 Checklist 自查表

功能分支提交前填写：

```markdown
## 代码分支合入自查表

分支名称：________________
合入目标：develop
提交日期：________________

### 时间对齐
- [ ] 时间索引类型和排序已确认
- [ ] 评估窗口 ID 已对齐 dual_window_evaluation_baseline

### Contract
- [ ] 数据 contract 差异已在文档中说明
- [ ] 输出 contract 差异已显式版本化
- [ ] 不存在同名不同义的字段

### 测试
- [ ] 新增测试可通过统一命令运行
- [ ] 核心变更有测试覆盖
- [ ] Smoke test 清单已更新（如适用）

### 文档
- [ ] 入口文档变更仅限导航
- [ ] 细节已下沉到专项文档
- [ ] 新增文档已索引

### 配置
- [ ] 新增配置已标注 config_status
- [ ] 默认入口已明确
- [ ] 旧配置已降级或归档（如适用）

### 验收产物
- [ ] 架构变更有对应文档
- [ ] 新增模块有配置示例
- [ ] 新依赖已说明

### 冲突处理
- [ ] 冲突文件已人工合并
- [ ] 简单冲突已在 commit message 说明
- [ ] 复杂冲突已准备详细说明文档

### 补充说明
（如有特殊情况，在此说明）
```

---

## 3. § 文档/方案吸收 Checklist

**适用示例：**
- `feature/execution-layer-v2` 🔜（设计文档吸收）

### 3.1 稳定文档 vs Working Memory 区分

**原则：** 只吸收稳定设计基线，不吸收过程型工作记忆。

```markdown
- [ ] 文档已盘点并分类
  - 稳定设计基线（可吸收）
  - Working memory（保留在分支或归档）
  - 待实现时重写（暂不吸收）

- [ ] 吸收清单已明确
  - 不存在"整分支并入"的情况
  - 每个文档的吸收理由已说明
```

**分类判断标准：**

| 类型 | 判断依据 | 示例 | 处理方式 |
|------|----------|------|----------|
| **稳定设计基线** | 架构决策、接口定义、phase 方案 | execution_layer_phase_implementation.md | 吸收进 develop |
| **Working memory** | 过程型思考、临时 todo、探索记录 | execution_layer_working_memory.md | 保留在分支或归档 |
| **待重写** | 依赖未实现功能、会过时的草稿 | 某个实验的临时结论 | 暂不吸收 |

**自查方式：**
- 在分支文档中标注每个文件的类型
- 准备吸收清单，说明每个文档为什么要吸收

**审查方式：**
- 查看吸收清单
- 确认 working memory 类型的文档没有被误判为稳定基线

**Working Memory 归档流程：**

- **归档时机：** 功能分支提交合并请求前
- **归档路径：** `docs/archive/<branch_name>_<YYYYMMDD>/`
- **归档操作：**
  1. 功能分支创建归档目录：`mkdir -p docs/archive/<branch_name>_<YYYYMMDD>/`
  2. 将 working memory 文档移动到归档目录
  3. 在归档目录下创建 README.md，说明归档内容和时间
  4. 提交归档 commit，注明 `archive: <branch_name> working memory`

- **维护者复核：**
  - 确认 working memory 文档已归档
  - 确认归档目录和 README.md 已创建

**归档示例：**
```bash
# 功能分支操作
mkdir -p docs/archive/execution_layer_v2_20260311/
mv docs/modules/execution_layer_working_memory.md docs/archive/execution_layer_v2_20260311/
echo "# Execution Layer V2 Working Memory Archive" > docs/archive/execution_layer_v2_20260311/README.md
git add docs/archive/execution_layer_v2_20260311/
git commit -m "archive: execution-layer-v2 working memory"
```

---

### 3.2 文档颗粒度符合规范

**原则：** 文档必须放在正确的目录，遵守 doc_governance.md 规则。

```markdown
- [ ] 文档归类正确
  - 已按 doc_governance.md 归类到正确目录
  - overview/ 只放项目级抽象
  - modules/ 只放系统分层和模块协同
  - research/ 只放研究方法和实验结论

- [ ] 文档命名符合规则
  - 长期文档不带日期
  - 短期文档带 YYYYMMDD 或 2026Q1
  - 不存在"应该在 modules/ 却放在 overview/"的情况
```

**自查方式：**
- 对照 `docs/overview/doc_governance.md` 的颗粒度规则
- 确认每个文档的目标目录

**审查方式：**
- 查看吸收清单中的目标路径
- 确认路径符合 doc_governance 规则

---

### 3.2.1 配置文件检查（如有变更）

**原则：** 若分支包含配置文件变更，需要额外检查配置状态标注。

```markdown
- [ ] 配置文件状态标注（如有 configs/ 变更）
  - 参考 §2.5 配置状态显式标注规则
  - 确认新增/修改的配置文件已标注 config_status（baseline/candidate/frozen）
  - 确认默认入口已明确
```

**自查方式：**
- 运行 `git diff develop --name-only | grep '^configs/'`
- 若有配置文件变更，逐个检查文件头的 config_status 注释

**审查方式：**
- 查看配置文件变更清单
- 确认每个配置文件的 config_status 标注

---

### 3.3 不存在功能误判

**原则：** 文档吸收 ≠ 功能完成，必须在任务文档中明确标注。

```markdown
- [ ] 实现状态明确
  - 文档吸收不等于功能完成，已在 develop.md 或 NEXT_STEPS.md 中明确标注
  - 若文档描述了"待实现"特性，develop 中有对应的实现任务

- [ ] 不存在误导
  - 不存在"文档已合并，所以执行层已完成"的表述
  - 文档标题和摘要明确标注"设计"或"方案"
```

**自查方式：**
- 检查吸收的文档是否有"已实现"的暗示
- 在 `develop.md` 中补充对应的实现任务

**审查方式：**
- 查看 `develop.md` 的任务列表
- 确认文档吸收后不会产生"功能已完成"的误解

---

### 3.4 文档/方案分支 Checklist 自查表

功能分支提交前填写：

```markdown
## 文档/方案吸收自查表

分支名称：________________
吸收目标：develop
提交日期：________________

### 变更清单（必填）

运行命令：`git diff develop --name-only`

#### 文档变更（docs/）
- [ ] 已列出所有 `docs/` 下的文件变更
- [ ] 每个文档已分类（稳定设计 / working memory / 待重写 / 导航层）

#### 配置变更（configs/）
- [ ] 已列出所有 `configs/` 下的文件变更
- [ ] 每个配置文件已检查 config_status 标注（如有变更）

#### 代码变更（src/, scripts/, tests/）
- [ ] 已列出所有代码相关的文件变更
- [ ] 已确认代码变更状态（设计探索 / 实现闭环）

#### 其他变更
- [ ] 根目录文件（README.md, NEXT_STEPS.md 等）
- [ ] 其他文件（pyproject.toml, .gitignore 等）

### 文档分类
- [ ] 已盘点分支文档，区分：稳定设计 / working memory / 待重写
- [ ] 吸收清单已明确，不存在整分支并入

### 颗粒度规范
- [ ] 文档归类符合 doc_governance.md
- [ ] 文档命名符合长期/短期规则
- [ ] 不存在目录错位

### 功能状态
- [ ] 文档吸收不等于功能完成，已在任务文档中明确
- [ ] 待实现特性有对应的实现任务
- [ ] 不存在误导性表述

### 吸收清单
（列出具体要吸收的文档及理由）

| 文档名称 | 目标路径 | 吸收理由 |
|----------|----------|----------|
|          |          |          |

### 补充说明
（如有特殊情况，在此说明）
```

---

### 3.5 兜底检查（确保无遗漏）

**原则：** 即使是文档/方案分支，也可能包含其他类型的文件变更，需要确认。

```markdown
- [ ] 配置文件（configs/）
  - 若有变更，参考 §2.5 配置状态显式标注规则
  - 确认 config_status 标注和默认入口明确

- [ ] 代码和脚本（src/, scripts/, tests/）
  - 若有变更，确认代码变更状态（设计探索 / 实现闭环）
  - 在任务文档中明确标注"代码未进入实现闭环"或"代码已完成"
  - 若代码已完成，应使用 §2 代码分支合入 Checklist

- [ ] 根目录文件（README.md, NEXT_STEPS.md, ROADMAP.md 等）
  - 确认变更仅限导航更新
  - 冲突时优先保留 develop 的导航结构

- [ ] 依赖文件（pyproject.toml, requirements.txt 等）
  - 若有变更，确认依赖更新的原因和必要性
  - 在文档或 commit message 中说明
```

**自查方式：**
- 运行 `git diff develop --name-status` 查看所有变更文件
- 逐个文件确认类型和吸收决策

**审查方式：**
- 查看变更清单，确认所有文件都有对应的检查项
- 确认非文档类型的变更有明确的处理策略

---

## 4. § 研究结论吸收 Checklist

**适用示例：**
- `feature/model-d1-research` 的协议、门禁、比较工具 🔜

### 4.1 研究协议卡片化

**原则：** 实验协议必须形成独立文档，可被其他研究引用。

```markdown
- [ ] 协议文档已形成
  - 独立文档存在（如 1d_experiment_protocol.md）
  - 协议包含：任务定义、数据集、特征组、标签、评估窗口、门禁阈值

- [ ] 协议可引用
  - 协议不依赖分支上下文
  - 其他研究可以引用该协议进行对照实验
```

**协议必须包含的要素：**
- 任务定义（如"预测未来 1 个交易日的涨跌方向"）
- 数据集 ID 和特征组 ID
- 标签定义（如"close-to-close return"）
- 评估窗口 ID（如 fixed_20230101_20250701）
- 门禁阈值（如"ICIR > 0.5"）

**自查方式：**
- 确认协议文档可以独立阅读，不需要翻其他分支文档
- 确认协议包含所有必要要素

**审查方式：**
- 查看研究协议文档
- 确认要素齐全

---

### 4.2 命名规则对齐 Registry（简化版）

**原则：** ID 必须显式记录，不能用口语化命名。

```markdown
- [ ] stock_pool_id 已记录
  - 使用 stock_pool_registry_baseline 中定义的 ID
  - 不存在"默认池"、"原始池"等口语化命名

- [ ] evaluation_window_id 已记录
  - 使用 dual_window_evaluation_baseline 中定义的 ID
  - 固定窗口和 latest 窗口都有记录

- [ ] dataset_id / feature_group_id 已记录
  - 命名规则清晰（当前可简化，G4 完成后升级）
  - 不存在同名不同义
```

**当前可用的 ID 基线：**
- stock_pool_id：`csi300`、`sector_single_*`、`sector_corr_*`、`sector_anti_corr_*`
- evaluation_window_id：`fixed_20230101_20250701`、`latest_rolling`

**自查方式：**
- 检查实验配置和报告中的 ID 字段
- 确认使用的是已注册的 ID，不是临时名称

**审查方式：**
- 查看实验配置 TOML 文件
- 确认 ID 字段存在且符合基线

**注：** G4 完成后，此检查项将升级为引用完整 ID 体系。

---

### 4.3 门禁规则可复用

**原则：** 门禁工具和阈值必须可被主线或其他研究复用。

```markdown
- [ ] 门禁工具已进入公用脚本
  - 比较脚本（如 compare_ic_reports.py）已进入 scripts/
  - 不依赖分支特定路径或临时配置

- [ ] 门禁阈值已显式记录
  - 阈值定义（如"ICIR > 0.5"）已在协议或文档中明确
  - 不是口头约定或隐含规则

- [ ] 门禁逻辑可复用
  - 主线或其他研究可以直接使用该门禁工具
  - 不需要重新实现或猜测逻辑
```

**自查方式：**
- 确认门禁脚本在 `scripts/` 下
- 确认阈值在协议文档中明确写出

**审查方式：**
- 运行门禁脚本，确认可以独立执行
- 查看文档中的阈值定义

---

### 4.4 不回写为默认主线

**原则：** 研究结论是候选方案，不能悄悄变成默认主线。

```markdown
- [ ] 研究结论明确标注
  - 研究结论明确标注为"独立研究"或"候选方案"
  - 不存在覆盖主线默认配置的行为

- [ ] 进入主线需验证
  - 若需进入主线，必须通过 baseline 验证流程
  - 不能因为"研究结论好"就直接替换主线默认
```

**自查方式：**
- 确认分支文档中标注"独立研究线"
- 确认没有修改主线的默认配置文件

**审查方式：**
- 查看配置文件变更
- 确认主线默认配置未被覆盖

---

### 4.5 研究结论分支 Checklist 自查表

功能分支提交前填写：

```markdown
## 研究结论吸收自查表

分支名称：________________
吸收目标：develop
提交日期：________________

### 研究协议
- [ ] 协议文档已形成（独立、可引用）
- [ ] 协议包含：任务定义、数据集、特征组、标签、窗口、门禁

### Registry 对齐
- [ ] stock_pool_id 已显式记录
- [ ] evaluation_window_id 已显式记录
- [ ] dataset_id / feature_group_id 已显式记录
- [ ] 不存在口语化命名

### 门禁规则
- [ ] 门禁工具已进入 scripts/
- [ ] 门禁阈值已在文档中明确
- [ ] 门禁逻辑可被主线或其他研究复用

### 主线边界
- [ ] 研究结论明确标注为"独立研究"或"候选"
- [ ] 不存在覆盖主线默认配置
- [ ] 进入主线需通过 baseline 验证（如适用）

### 补充说明
（如有特殊情况，在此说明）
```

---

## 5. Checklist 使用流程

### 5.1 功能分支侧（提交前）

1. 根据分支类型选择对应的 Checklist
2. 逐项自查，填写自查表
3. 准备冲突处理记录（如有冲突）
4. 将自查表连同分支提交给 develop 维护者

### 5.2 Develop 维护者侧（审查时）

1. 接收功能分支的自查表
2. 复核每个检查项：
   - ✅ 通过：在审查记录中标注
   - ⚠️  有疑问：与功能分支负责人沟通确认
   - ❌ 不通过：打回或协助修正
3. 所有检查项通过后，执行合并
4. 在 merge commit message 或审计文档中记录审查结果

### 5.3 审查结果示例

```markdown
## Merge Audit: feature/model-d1-research → develop

审查日期：2026-03-11
审查人：[姓名]
Checklist 类型：§ 研究结论吸收

### 审查结果
- ✅ 研究协议已形成（1d_experiment_protocol.md）
- ✅ Registry 对齐（stock_pool_id=csi300, evaluation_window_id 已对齐）
- ✅ 门禁工具可复用（compare_ic_reports.py 增强）
- ✅ 主线边界明确（1d 为独立研究线）
- ⚠️  冲突文件需人工合并（docs/README.md, docs/research/README.md, scripts/run_xgboost_rolling_retrain_regime.py）

### 冲突处理策略
（见单独的冲突合并文档）

### 结论
**通过，可合并**
```

---

## 6. 版本升级说明

**当前版本：** v1.0（简化版）

**已知限制：**
- 配置状态检查项使用简化规则，依赖 G4 完成后升级
- ID 体系检查项仅覆盖已有基线（stock_pool、evaluation_window），完整 ID 体系待 G4 定义

**升级计划：**
- G4（配置与产物规范）完成后，更新 § 2.5 和 § 4.2
- G2（docs 治理）完成后，更新 § 2.4 和 § 3.2 的引用规范

---

## 7. 关联文档

- [分支任务索引](../branch_tasks/README.md)
- [Develop 任务文档](../branch_tasks/develop.md)
- [分支整理与基线对齐审计](branch_consolidation_audit_20260311.md)
- [股票池 Registry 基线](../modules/stock_pool_registry_baseline_20260311.md)
- [双窗口评估基线](dual_window_evaluation_baseline_20260311.md)
- [文档命名与落盘规则](doc_governance.md)
