# `feature/model-d1-research` 合并指南（2026-03-11）

## 0. 文档用途

本文档是 `feature/model-d1-research` 分支合并到 `develop` 的专属操作指南。

**完整冲突分析报告：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)

---

## 1. 分支概况

**分支名称：** `feature/model-d1-research`
**分支角色：** 1d 独立研究线
**文档差异：** 30+ 个文档文件
**预估处理时间：** 45 分钟

---

## 2. 冲突分类统计

| 类型 | 数量 | 处理方式 | 优先级 |
|------|------|---------|--------|
| **缺失治理基线文档** | 5 | 自动合并 | P3（零成本） |
| **入口文档冲突** | 5 | 人工三方合并 | P0（30 分钟） |
| **分支任务文档过时** | 4 | 自动合并 | P3（零成本） |
| **1d 专属研究文档** | 5 | 挑选吸收或归档 | P1/P2（15 分钟） |
| **Archive 差异** | 6 | 自动合并 | P3（零成本） |

---

## 3. 冲突详情

### 3.1 缺失治理基线文档（P3 - 自动合并）

**现象：** 分支缺少治理期产出的 4 个核心文档

| 文件 | develop 状态 | 分支状态 | 差异 |
|------|-------------|----------|------|
| merge_audit_checklist_20260311.md | ✅ 有（782 行） | ❌ 无 | -782 行 |
| doc_lifecycle_rules_20260311.md | ✅ 有（201 行） | ❌ 无 | -201 行 |
| shared_layer_inventory_20260311.md | ✅ 有（383 行） | ❌ 无 | -383 行 |
| config_and_artifact_naming_20260311.md | ✅ 有（554 行） | ❌ 无 | -554 行 |
| doc_governance.md | ✅ 已更新 | ⚠️ 旧版本 | +1/-33 |

**处理方式：** `git merge develop` 自动合并，无需人工干预。

---

### 3.2 入口文档冲突（P0 - 人工三方合并）

**现象：** 分支修改了入口文档，违反 G2 集中制规则

| 文件 | 冲突类型 | 合并策略 |
|------|---------|---------|
| `docs/README.md` | 新增索引 + 修改描述 | **三方合并** |
| `docs/research/README.md` | 新增 1d 文档索引 | **三方合并** |
| `docs/modules/README.md` | 删除部分条目 | **完全保留 develop** |
| `docs/overview/README.md` | 删除部分条目 | **完全保留 develop** |
| `docs/branch_tasks/README.md` | 分支未更新 | **完全保留 develop** |

**冲突详情（docs/README.md）：**
```diff
# 分支新增（应保留）
+5. [research/1d_experiment_protocol.md](...)
+6. [research/1d_independent_model_execution_strategy_20260309.md](...)

# 分支删除（应恢复，保留 develop 描述）
-主线推荐层默认把 `3d/5d/10d` 三头聚合为单一 `alpha_score`
```

**冲突详情（docs/research/README.md）：**
```diff
# 分支新增（应保留）
+- [1d_experiment_protocol.md](...)：`1d` 独立实验协议
+- [IC评估体系最小改造清单与计划.md](...)：专项改造任务（已完成）
+- [IC评估体系改造Prompt包.md](...)：执行辅助材料（已完成）

# 分支删除（应恢复，develop 保留了这个文档）
-- [mainline_3510d_development_retrospective_20260310.md](...)
```

**合并原则（基于 G2 集中制）：**
- ✅ 保留 develop 的导航结构和描述性文字
- ✅ 补充分支新增的文档索引条目
- ❌ 删除分支对描述性文字的修改

---

### 3.3 1d 专属研究文档（P1/P2 - 挑选吸收）

| 文档 | 状态 | 处理方式 | 优先级 |
|------|------|---------|--------|
| `1d_experiment_protocol.md` | 1d 研究协议 | ✅ 应合入（已被 G3/G4 引用） | P1 |
| `1d_independent_model_research_plan.md` | 1d 研究计划 | ✅ 应合入 | P1 |
| `daily_cs_eval_workflow.md` | Daily-CS 评估流程 | ✅ 应合入 | P1 |
| `IC评估体系最小改造清单与计划.md` | IC 改造任务 | ⚠️ 应归档（专项已完成） | P2 |
| `IC评估体系改造Prompt包.md` | IC 改造辅助 | ⚠️ 应归档（专项已完成） | P2 |

---

## 4. 合并执行计划

### 阶段 1：在分支上合并 develop

```bash
# 1. 切换到 d1-research 分支
git checkout feature/model-d1-research

# 2. 合并 develop（会遇到 5 个入口文档冲突）
git merge develop

# 预期输出：
# Auto-merging docs/README.md
# CONFLICT (content): Merge conflict in docs/README.md
# Auto-merging docs/research/README.md
# CONFLICT (content): Merge conflict in docs/research/README.md
# ... (共 5 个冲突)
```

---

### 阶段 2：解决入口文档冲突

#### 步骤 2.1：简单冲突（完全保留 develop）

```bash
# 3 个文件直接取 develop 版本
git checkout --ours docs/modules/README.md
git checkout --ours docs/overview/README.md
git checkout --ours docs/branch_tasks/README.md
```

#### 步骤 2.2：复杂冲突（三方合并）

**docs/README.md 合并模板：**

```markdown
# 保留 develop 的导航结构（完整保留）
## 快速入口

1. [../README.md](../README.md)
2. [../NEXT_STEPS.md](../NEXT_STEPS.md)
3. [../ROADMAP.md](../ROADMAP.md)
4. [modules/model_line_boundaries_1d_vs_3510d_20260309.md](...)
5. [research/1d_experiment_protocol.md](...)  # ← 补充分支新增
6. [research/1d_independent_model_execution_strategy_20260309.md](...)  # ← 补充分支新增
7. [interfaces/README.md](interfaces/README.md)

原因是当前真正需要先读清楚的，不只是目录结构，而是：

- 主线模型固定为 `3d/5d/10d`
- 主线推荐层默认把 `3d/5d/10d` 三头聚合为单一 `alpha_score`  # ← 保留 develop 描述
- `1d` 只作为独立研究线
- 执行层是当前第一优先级

... （保留 develop 其余内容）

## 详细阅读指南

- 需要确认当前开发优先级时，从 [../NEXT_STEPS.md](../NEXT_STEPS.md) 开始。
- 需要做主线模型开发前，先读 [modules/model_line_boundaries_1d_vs_3510d_20260309.md](...)。
- 需要推进 `1d` 研究前，先读 [research/1d_experiment_protocol.md](...)，再读 [research/1d_independent_model_execution_strategy_20260309.md](...)。  # ← 补充分支新增
- 需要确认协议、字段和交易约束时，转到 [interfaces/README.md](interfaces/README.md)。
```

**手工编辑命令：**

```bash
# 用你喜欢的编辑器打开
vim docs/README.md

# 参考上面的模板，执行三方合并：
# 1. 保留 develop 的所有导航结构和描述
# 2. 补充分支新增的索引条目（第 5、6 条）
# 3. 删除分支对描述性文字的修改
```

---

**docs/research/README.md 合并模板：**

```markdown
# 保留 develop 的推荐阅读顺序（完整保留）
## 推荐阅读顺序

1. [research_checklist.md](research_checklist.md)
2. [1d_experiment_protocol.md](1d_experiment_protocol.md)  # ← 补充分支新增
3. [1d_independent_model_execution_strategy_20260309.md](...)
4. [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)
5. [数据窗口结构的区别.md](...)
6. [多头输出和数据切分.md](...)
7. [警惕伪信号.md](...)
8. [1d_independent_model_research_plan.md](1d_independent_model_research_plan.md)
9. [future_roadmap_suggestions.md](future_roadmap_suggestions.md)
10. [future_roadmap_suggestions_20260307.md](...)（历史版）
11. [multilevel_tuning_plan_20260307.md](multilevel_tuning_plan_20260307.md)
12. [mainline_3510d_development_retrospective_20260310.md](...)  # ← 保留 develop 索引

## 文档分组

- [research_checklist.md](research_checklist.md)：研究主清单与门禁
- [1d_experiment_protocol.md](1d_experiment_protocol.md)：`1d` 独立实验协议  # ← 补充分支新增
- [1d_independent_model_execution_strategy_20260309.md](...)：`1d` 独立研究线的执行顺序与数据节奏
- [1d_independent_model_research_plan.md](1d_independent_model_research_plan.md)：`1d` 补充研究提纲
- [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)：Daily-CS 评估流程
- [数据窗口结构的区别.md](...)：训练窗口与重训策略
- [多头输出和数据切分.md](...)：默认多头配置与固定切分数值
- [警惕伪信号.md](...)：伪信号与回测偏差风险
- [future_roadmap_suggestions.md](future_roadmap_suggestions.md)：最近一轮研究路线校准
- [multilevel_tuning_plan_20260307.md](multilevel_tuning_plan_20260307.md)：LSTM / XGBoost 多级别自动微调方案
- [mainline_3510d_development_retrospective_20260310.md](...)：本轮 `3d/5d/10d` 主模型分支开发复盘  # ← 保留 develop 索引

## 当前默认研究口径

- 默认主线仍是 `3d/5d/10d`，不是 `1d`。
- `1d` 当前只作为独立短周期研究线推进，不进入默认主线打分。
- 默认推荐打分先把 `pred_3d/pred_5d/pred_10d` 聚合为单一 `alpha_score`，默认权重 `0.2 / 0.4 / 0.4`。  # ← 保留 develop 描述
- 默认训练节奏仍以 `weekly retrain + daily inference + maturity-gated training pool + walk-forward evaluation` 为主。
- 多级微调仍采用配置文件驱动，但不能覆盖模型线边界规则。
- 任何 `1d` 结论进入默认流程前，都必须先同步到 `overview` / `modules` / `interfaces` 层。

（保留 develop 其余内容）
```

**手工编辑命令：**

```bash
# 编辑 docs/research/README.md
vim docs/research/README.md

# 执行三方合并：
# 1. 保留 develop 的推荐阅读顺序和文档分组
# 2. 补充分支新增的 1d_experiment_protocol.md 索引（第 2 条）
# 3. 保留 develop 的"当前默认研究口径"描述
```

---

#### 步骤 2.3：提交合并结果

```bash
# 添加所有已解决的冲突文件
git add docs/README.md
git add docs/research/README.md
git add docs/modules/README.md
git add docs/overview/README.md
git add docs/branch_tasks/README.md

# 提交合并
git commit -m "merge: resolve docs conflicts with develop (preserve develop structure, add 1d indexes)"
```

---

### 阶段 3：归档 IC 改造文档（P2）

```bash
# 仍在 feature/model-d1-research 分支

# 移动 IC 改造相关文档到已有归档目录
mv "docs/research/IC评估体系最小改造清单与计划.md" \
   docs/archive/ic_reform_completed_20260305/

mv "docs/research/IC评估体系改造Prompt包.md" \
   docs/archive/ic_reform_completed_20260305/

# 更新 research/README.md，移除这两个文档的索引
# （手工编辑，删除 IC 改造相关的两行）
vim docs/research/README.md

# 提交归档
git add -A
git commit -m "archive: IC reform docs to archive/ic_reform_completed_20260305/"
```

---

### 阶段 4：切回 develop，完成合并

```bash
# 切回 develop
git checkout develop

# 合并 d1-research 分支（此时已解决所有冲突）
git merge feature/model-d1-research

# 检查合并结果
git log --oneline -5
git diff HEAD~1 --stat
```

---

## 5. 合并验证清单

合并完成后，逐项检查：

- [ ] 治理基线文档已存在（4 个）
  ```bash
  ls -la docs/overview/merge_audit_checklist_20260311.md
  ls -la docs/overview/doc_lifecycle_rules_20260311.md
  ls -la docs/overview/shared_layer_inventory_20260311.md
  ls -la docs/overview/config_and_artifact_naming_20260311.md
  ```

- [ ] 入口文档只有导航内容，无长文本描述
  ```bash
  # 检查 docs/README.md 中是否保留了 develop 的描述
  grep "主线推荐层默认把" docs/README.md
  # 应该输出：- 主线推荐层默认把 `3d/5d/10d` 三头聚合为单一 `alpha_score`
  ```

- [ ] 1d 专属文档索引已补充
  ```bash
  grep "1d_experiment_protocol" docs/README.md
  grep "1d_experiment_protocol" docs/research/README.md
  # 应该都能找到索引条目
  ```

- [ ] IC 改造文档已归档
  ```bash
  ls -la docs/archive/ic_reform_completed_20260305/IC评估体系*
  # 应该显示 2 个文件

  grep "IC评估体系" docs/research/README.md
  # 不应该找到（或只有归档说明，无索引）
  ```

- [ ] 分支任务文档已同步 develop 更新
  ```bash
  grep "G1/G2/G3/G4" docs/branch_tasks/feature_model_d1_research.md
  # 应该能找到治理专题引用
  ```

- [ ] INVENTORY.md 已包含新增文档
  ```bash
  grep "branch_baseline_conflict_analysis" docs/INVENTORY.md
  # 应该输出：- `overview/branch_baseline_conflict_analysis_20260311.md` — `active` — ...
  ```

---

## 6. 风险与注意事项

### 6.1 入口文档冲突风险

**风险：** 三方合并时可能误删有价值的索引条目

**缓解措施：**
- 合并前备份当前 README.md 内容
  ```bash
  cp docs/README.md docs/README.md.backup
  cp docs/research/README.md docs/research/README.md.backup
  ```
- 合并后对比，确保新增索引已补充
  ```bash
  diff docs/README.md.backup docs/README.md
  ```

### 6.2 索引过时风险

**风险：** 归档文档后，README.md 索引仍指向已归档文档

**缓解措施：**
- 归档后立即检查所有引用
  ```bash
  grep -r "IC评估体系" docs/ | grep -v archive
  # 应该没有输出（或只有合理的说明）
  ```

---

## 7. 完成后清理（可选）

```bash
# 删除备份文件
rm docs/README.md.backup
rm docs/research/README.md.backup

# 如果不再需要分支（合并后）
git branch -d feature/model-d1-research  # 本地删除
git push origin --delete feature/model-d1-research  # 远程删除（需确认）
```

---

## 8. 关联文档

- **完整冲突分析：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)
- **G1 Merge/Audit Checklist：** [../overview/merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md)
- **G2 文档生命周期规则：** [../overview/doc_lifecycle_rules_20260311.md](../overview/doc_lifecycle_rules_20260311.md)
- **分支任务文档：** [feature_model_d1_research.md](feature_model_d1_research.md)
