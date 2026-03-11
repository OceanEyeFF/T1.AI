# G1 Merge/Audit Checklist 验证方案（2026-03-11）

## 0. 验证目的

在真正应用 [merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md) 之前，先在独立分支上验证其可操作性。

**核心目标：**
- 验证 checklist 的每个检查项是否可判断、无歧义
- 验证双重验证流程（自查+复核）是否顺畅
- 发现并修正 checklist 的不足之处
- 为后续真实合并提供参考示例

**验证原则：**
- 在独立分支 `feature/g1-validation` 上进行，不污染 `develop`
- 只验证 checklist 填写流程，不真正合并代码
- 记录所有问题和改进建议
- 验证完成后归档并删除验证分支

---

## 1. 验证对象

**选定分支：** `feature/execution-layer-v2`

**选择理由：**
- 纯文档/方案分支，适合验证 § 文档/方案吸收 Checklist
- 验证难度较低，不涉及代码合并冲突
- 已有明确的文档分类需求（稳定设计 vs working memory）

**适用 Checklist：**
- § 文档/方案吸收 Checklist（主验证对象）
- 部分通用检查项（如文档入口导航化）

---

## 2. 验证流程

### 阶段 1：准备验证分支

```bash
# 从 develop 创建验证分支
git checkout develop
git checkout -b feature/g1-validation

# 标记验证分支的用途
echo "This branch is for G1 checklist validation only" > G1_VALIDATION_README.md
git add G1_VALIDATION_README.md
git commit -m "init: create G1 validation branch"
```

**验证点：**
- [ ] 验证分支已创建
- [ ] 验证分支不会影响 develop 和其他功能分支

---

### 阶段 2：模拟功能分支自查

**角色：** 功能分支负责人（execution-layer-v2）

**任务：** 按照 § 文档/方案吸收 Checklist 填写自查表

#### 2.1 盘点分支文档

**操作：**
1. 切换到 `feature/execution-layer-v2` 分支（或其 worktree）
2. 列出所有文档变更：
   ```bash
   cd /home/oceaneye/github/T1.AI-exec
   git diff develop --name-only | grep "\.md$"
   ```
3. 对每个文档标注类型：
   - 稳定设计基线（可吸收）
   - Working memory（保留在分支或归档）
   - 待重写（暂不吸收）

**输出产物：**
- 文档分类清单（Markdown 表格）
- 吸收理由说明

**验证点：**
- [ ] 分类标准是否清晰（能否快速判断每个文档属于哪类）
- [ ] 是否存在"难以判断"的边界案例
- [ ] 吸收理由是否充分

---

#### 2.2 检查文档颗粒度

**操作：**
1. 对照 [doc_governance.md](../overview/doc_governance.md)
2. 确认每个文档的目标目录是否正确
3. 检查文档命名是否符合长期/短期规则

**验证点：**
- [ ] doc_governance.md 规则是否足够明确
- [ ] 是否存在"不知道放哪里"的文档
- [ ] 命名规则是否有遗漏场景

---

#### 2.3 确认不存在功能误判

**操作：**
1. 检查文档中是否有"已实现"的暗示
2. 在 `develop.md` 中补充对应的实现任务（如需要）

**验证点：**
- [ ] 如何判断"文档是否误导功能已完成"
- [ ] develop.md 中的实现任务描述是否清晰

---

#### 2.4 填写自查表

**操作：**
在 `feature/g1-validation` 分支创建自查表文件：

```bash
cd /home/oceaneye/github/T1.AI
git checkout feature/g1-validation
mkdir -p validation_artifacts
touch validation_artifacts/execution_layer_v2_self_check.md
```

**自查表内容：**
```markdown
## 文档/方案吸收自查表

分支名称：feature/execution-layer-v2
吸收目标：develop
提交日期：2026-03-11
填写人：[验证者]

### 文档分类
- [ ] 已盘点分支文档，区分：稳定设计 / working memory / 待重写
- [ ] 吸收清单已明确，不存在整分支并入

**文档分类清单：**

| 文档名称 | 类型 | 目标路径 | 吸收理由/保留理由 |
|----------|------|----------|-------------------|
| execution_layer_branch_plan_20260309.md | 稳定设计 | docs/research/ | 执行层分支计划，可作为历史参考 |
| execution_layer_phase_implementation.md | 稳定设计 | docs/technical/ | Phase 0-3 实施方案，后续实现依据 |
| portfolio_manager_algorithm.md | 稳定设计 | docs/technical/ | PortfolioManager 算法伪代码 |
| phase0_design_research_single_score_input.md | 稳定设计 | docs/technical/ | 单一评分输入设计决策 |
| execution_layer_working_memory.md | Working memory | 保留在分支 | 过程型工作记忆，不作为长期基线 |

**填写时遇到的问题：**
（记录每个检查项是否清晰、是否有歧义）

### 颗粒度规范
- [ ] 文档归类符合 doc_governance.md
- [ ] 文档命名符合长期/短期规则
- [ ] 不存在目录错位

**检查记录：**
（是否遇到"不知道放哪里"的文档）

### 功能状态
- [ ] 文档吸收不等于功能完成，已在任务文档中明确
- [ ] 待实现特性有对应的实现任务
- [ ] 不存在误导性表述

**检查记录：**
（develop.md 中是否需要补充实现任务）

### 补充说明
（填写过程中的困惑、建议）
```

**验证点：**
- [ ] 自查表是否容易填写
- [ ] 是否有无法判断的检查项
- [ ] 是否需要补充说明或示例

---

### 阶段 3：模拟 develop 维护者审查

**角色：** develop 维护者

**任务：** 复核自查表，提出问题或确认通过

#### 3.1 接收自查表

**操作：**
在 `feature/g1-validation` 分支查看自查表：
```bash
cat validation_artifacts/execution_layer_v2_self_check.md
```

#### 3.2 逐项复核

**复核清单：**
```markdown
## Develop 维护者复核记录

审查日期：2026-03-11
审查人：[验证者]
Checklist 类型：§ 文档/方案吸收

### 文档分类复核
- [ ] 文档分类是否合理
  - ✅/⚠️/❌：______
  - 问题/建议：______

- [ ] 吸收清单是否明确
  - ✅/⚠️/❌：______
  - 问题/建议：______

### 颗粒度规范复核
- [ ] 文档归类是否符合 doc_governance
  - ✅/⚠️/❌：______
  - 问题/建议：______

- [ ] 文档命名是否规范
  - ✅/⚠️/❌：______
  - 问题/建议：______

### 功能状态复核
- [ ] 是否存在功能误判
  - ✅/⚠️/❌：______
  - 问题/建议：______

### 审查结论
- [ ] 通过，可吸收
- [ ] 有疑问，需沟通确认
- [ ] 不通过，需修正

### 复核过程中的发现
（记录 checklist 的不足、改进建议）
```

**验证点：**
- [ ] 复核是否能快速进行
- [ ] 是否有主观判断导致的分歧
- [ ] checklist 是否提供了足够的判断依据

---

### 阶段 4：问题汇总与改进

**操作：**
在 `feature/g1-validation` 分支创建问题汇总文档：

```bash
touch validation_artifacts/g1_validation_findings.md
```

**问题汇总模板：**
```markdown
# G1 Checklist 验证发现（2026-03-11）

## 验证对象
- 分支：feature/execution-layer-v2
- Checklist：§ 文档/方案吸收

## 发现的问题

### 1. 检查项不清晰
**问题描述：**
（哪个检查项不清晰、为什么）

**改进建议：**
（如何修改 checklist）

### 2. 判断标准主观
**问题描述：**
（哪个检查项依赖主观判断）

**改进建议：**
（如何提供客观标准）

### 3. 缺少示例
**问题描述：**
（哪个检查项需要补充示例）

**改进建议：**
（提供什么示例）

### 4. 流程不顺畅
**问题描述：**
（双重验证流程的哪个环节有问题）

**改进建议：**
（如何优化流程）

## 验证成功的部分
（哪些检查项清晰、易用、无歧义）

## 总体评价
- [ ] Checklist 可以直接应用
- [ ] Checklist 需要小幅修正
- [ ] Checklist 需要大幅改进

## 下一步行动
（根据验证结果，是否需要修改 merge_audit_checklist_20260311.md）
```

---

### 阶段 5：归档与清理

**操作：**

#### 5.1 归档验证产物

```bash
# 将验证产物移入 docs/archive/
mkdir -p docs/archive/g1_validation_20260311
mv validation_artifacts/* docs/archive/g1_validation_20260311/

git add docs/archive/g1_validation_20260311/
git commit -m "archive: G1 checklist validation artifacts"
```

#### 5.2 更新 merge_audit_checklist（如需要）

根据验证发现的问题，修改 `docs/overview/merge_audit_checklist_20260311.md`。

#### 5.3 删除验证分支

```bash
git checkout develop
git branch -D feature/g1-validation
```

**验证点：**
- [ ] 验证产物已归档到 docs/archive/
- [ ] 验证分支已清理
- [ ] checklist 已根据验证结果改进（如需要）

---

## 3. 验证检查清单

### 验证前准备
- [ ] 已阅读 merge_audit_checklist_20260311.md
- [ ] 已创建 feature/g1-validation 分支
- [ ] 已准备自查表和复核表模板

### 自查阶段验证点
- [ ] 文档分类是否容易判断
- [ ] 吸收理由是否充分
- [ ] 文档颗粒度规则是否清晰
- [ ] 功能误判是否容易识别
- [ ] 自查表是否容易填写

### 复核阶段验证点
- [ ] 复核是否能快速进行
- [ ] 是否有主观判断导致的分歧
- [ ] checklist 是否提供足够的判断依据
- [ ] 双重验证流程是否顺畅

### 问题汇总验证点
- [ ] 所有问题已记录
- [ ] 改进建议已提出
- [ ] 是否需要修改 checklist

### 归档清理验证点
- [ ] 验证产物已归档
- [ ] 验证分支已删除
- [ ] checklist 已改进（如需要）

---

## 4. 预期时间估算

| 阶段 | 预计耗时 |
|------|----------|
| 准备验证分支 | 5 分钟 |
| 模拟功能分支自查 | 30 分钟 |
| 模拟 develop 维护者审查 | 20 分钟 |
| 问题汇总与改进 | 30 分钟 |
| 归档与清理 | 10 分钟 |
| **总计** | **约 1.5 小时** |

---

## 5. 验证成功标准

满足以下条件之一即可认为验证成功：

1. **理想情况**：
   - 所有检查项清晰无歧义
   - 自查表易于填写
   - 复核流程顺畅
   - 无需修改 checklist

2. **可接受情况**：
   - 发现少量（≤3 个）不清晰的检查项
   - 提出改进建议并修改 checklist
   - 修改后的 checklist 逻辑自洽

3. **需要重新验证**：
   - 发现大量（>3 个）问题
   - checklist 需要大幅改进
   - 修改后需要再次验证

---

## 6. 验证后行动

### 如果验证成功
- [ ] 将验证产物归档到 docs/archive/g1_validation_20260311/
- [ ] 在 develop_governance_backlog_20260311.md 中标记 G1 已验证
- [ ] 可以开始真正的分支合入流程

### 如果需要改进
- [ ] 根据验证发现修改 merge_audit_checklist_20260311.md
- [ ] 在 checklist 中补充示例或说明
- [ ] 考虑是否需要再次验证

### 如果需要重新设计
- [ ] 记录当前 checklist 的根本问题
- [ ] 重新设计检查项和判断标准
- [ ] 必须再次验证

---

## 7. 关联文档

- [Merge/Audit Checklist](../overview/merge_audit_checklist_20260311.md) - 被验证对象
- [Develop 任务文档](develop.md) - G1 任务状态
- [治理总清单](develop_governance_backlog_20260311.md) - G1 在治理全局中的位置
- [执行层分支任务](feature_execution_layer_v2.md) - 验证对象分支
