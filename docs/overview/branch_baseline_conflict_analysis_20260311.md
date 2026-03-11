# 分支与 Develop 基线文档冲突分析（2026-03-11）

## 0. 分析背景

治理期（G1/G2/G3/G4）已完成，develop 分支产出 4 个核心基线文档。
本分析检查三个功能分支与 develop 基线文档的冲突情况，为后续分支合入提供决策依据。

**检查对象：**
- `feature/model-d1-research`（1d 独立研究线）
- `feature/execution-layer-v2`（执行层设计线）
- `feature/model-3d-5d-10d-head`（主模型线，代码已合并但分支未快进）

**检查时间：** 2026-03-11，治理期闭合 commit `f129efe` 后

---

## 1. 冲突类型总览

### 1.1 文档缺失型（非冲突）

**现象：** 三个分支都**缺少**治理期产出的 4 个核心基线文档

| 文档 | develop 状态 | 分支状态 | 差异规模 |
|------|-------------|----------|---------|
| merge_audit_checklist_20260311.md | ✅ 已有（782 行） | ❌ 缺失 | -782 行 |
| doc_lifecycle_rules_20260311.md | ✅ 已有（201 行） | ❌ 缺失 | -201 行 |
| shared_layer_inventory_20260311.md | ✅ 已有（383 行） | ❌ 缺失 | -383 行 |
| config_and_artifact_naming_20260311.md | ✅ 已有（554 行） | ❌ 缺失 | -554 行 |
| doc_governance.md | ✅ 已更新 | ⚠️ 旧版本 | +1/-33 |

**性质：** 单向缺失，非冲突。分支需要合并 develop 更新，无需人工决策。

**建议：**
- 三个分支都应先 `git merge develop` 或 `git rebase develop`
- 无需人工解决冲突（这些文档在分支中不存在）

---

### 1.2 入口文档修改型（真实冲突）

**现象：** 分支修改了入口文档（README.md 族），违反 G2 集中制规则

#### d1-research 分支的入口文档差异

| 文件 | develop 状态 | d1 分支修改 | 冲突类型 |
|------|-------------|------------|---------|
| docs/README.md | 治理期已更新 | 新增导航条目 + 修改描述 | ⚠️ 内容冲突 |
| docs/research/README.md | 治理期已更新 | 新增 1d_experiment_protocol.md 索引 | ⚠️ 内容冲突 |
| docs/modules/README.md | 治理期已更新 | 删除部分条目 | ⚠️ 内容冲突 |
| docs/overview/README.md | 治理期已更新 | 删除部分条目 | ⚠️ 内容冲突 |
| docs/branch_tasks/README.md | 治理期已更新 | 分支未更新 | ⚠️ 索引过时 |

**冲突详情（docs/README.md）：**
```diff
# d1-research 新增
+5. [research/1d_experiment_protocol.md](research/1d_experiment_protocol.md)
+6. [research/1d_independent_model_execution_strategy_20260309.md](...)

# d1-research 删除
-主线推荐层默认把 `3d/5d/10d` 三头聚合为单一 `alpha_score`
```

**冲突详情（docs/research/README.md）：**
```diff
# d1-research 新增
+- [1d_experiment_protocol.md](1d_experiment_protocol.md)：`1d` 独立实验协议
+- [IC评估体系最小改造清单与计划.md](...)：专项改造任务
+- [IC评估体系改造Prompt包.md](...)：执行辅助材料

# d1-research 删除（develop 保留）
-- [mainline_3510d_development_retrospective_20260310.md](...)
```

**性质：** 真实冲突，需要人工决策合并策略。

**建议（基于 G2 集中制规则）：**
1. **保留 develop 的导航结构**（作为基底）
2. **吸收 d1 分支的新增条目**（新文档索引）
3. **删除 d1 分支的描述性文字修改**（入口文档只做导航，不承载细节）
4. **合并后在 develop 上统一更新入口文档**

---

#### execution-layer-v2 分支的入口文档差异

| 文件 | develop 状态 | execution 分支修改 | 冲突类型 |
|------|-------------|-------------------|---------|
| docs/README.md | 治理期已更新 | 新增执行层文档索引 | ⚠️ 内容冲突 |
| docs/research/README.md | 治理期已更新 | 新增执行层计划索引 | ⚠️ 内容冲突 |

**性质：** 与 d1-research 类似，属于入口文档集中制冲突。

**建议：** 同 d1-research 处理策略。

---

#### 3d-5d-10d-head 分支的入口文档差异

**现象：** 与其他两个分支完全一致（代码已合并，但分支未快进）

**建议：** 快进分支到最新 develop，或直接删除分支（代码已进主线）。

---

### 1.3 分支任务文档同步型（已自动解决）

**现象：** 治理期已同步更新三个分支的任务文档

| 分支 | 任务文档 | develop 状态 | 分支状态 | 差异 |
|------|---------|-------------|----------|------|
| d1-research | feature_model_d1_research.md | 已更新（G1/G2/G3/G4 引用） | 未更新 | ⚠️ 需合并 |
| execution-layer-v2 | feature_execution_layer_v2.md | 已更新（G1/G2/G3/G4 引用） | 未更新 | ⚠️ 需合并 |
| 3d-5d-10d-head | feature_model_3d_5d_10d_head.md | 已更新（归档标记） | 未更新 | ⚠️ 需合并 |

**性质：** develop 单向更新，分支需要合并但无冲突。

**建议：** 合并 develop 后，分支自动获得治理期同步的任务文档更新。

---

### 1.4 研究文档独立型（可共存）

**现象：** 各分支有独立的研究文档，develop 没有

#### d1-research 专属文档

| 文档 | 状态 | 是否应合入 develop |
|------|------|-------------------|
| 1d_experiment_protocol.md | 1d 研究协议 | ✅ 应合入（已在 G3/G4 引用） |
| 1d_independent_model_research_plan.md | 1d 研究计划 | ✅ 应合入 |
| daily_cs_eval_workflow.md | Daily-CS 评估流程 | ✅ 应合入 |
| IC评估体系最小改造清单与计划.md | IC 改造任务（已完成） | ⚠️ 建议归档 |
| IC评估体系改造Prompt包.md | IC 改造辅助（已完成） | ⚠️ 建议归档 |

#### execution-layer-v2 专属文档

| 文档 | 状态 | 是否应合入 develop |
|------|------|-------------------|
| execution_layer_working_memory.md | Working Memory | ❌ 应归档（G1 规则） |
| execution_layer_branch_plan_20260309.md | 执行层计划 | ✅ 应吸收（稳定设计） |

**性质：** 分支专属资产，部分应合入，部分应归档。

**建议：**
- d1 研究协议文档：应合入 develop，补齐 research/ 索引
- IC 改造相关文档：已完成的专项任务，建议归档到 `archive/ic_reform_completed_20260305/`（已有归档目录）
- execution-layer working memory：按 G1 § 3.1 归档流程处理

---

## 2. 分支冲突详细盘点

### 2.1 feature/model-d1-research

**总体差异：** 30+ 个文档文件差异

**分类统计：**

| 类型 | 数量 | 文件示例 |
|------|------|---------|
| 缺失治理基线文档 | 5 | merge_audit_checklist, doc_lifecycle_rules, shared_layer_inventory, config_naming, doc_governance |
| 入口文档冲突 | 5 | docs/README.md, research/README.md, modules/README.md, overview/README.md, branch_tasks/README.md |
| 分支任务文档过时 | 4 | develop.md, develop_governance_backlog, feature_d1_research.md, feature_execution.md |
| 1d 专属研究文档 | 5 | 1d_experiment_protocol, 1d_research_plan, daily_cs_eval, IC 改造 2 个 |
| Archive 差异 | 6 | G1 验证归档文件（develop 有，分支无） |
| 其他文档 | 5+ | model_line_boundaries, system_io_spec, topic_maps, future_roadmap |

**优先级排序：**

| 优先级 | 冲突类型 | 处理策略 | 预估工作量 |
|--------|---------|---------|-----------|
| **P0** | 入口文档冲突（5 个） | 人工三方合并 | 中等（30 分钟） |
| **P1** | 1d 专属文档吸收（3 个） | 直接合入 + 索引更新 | 低（10 分钟） |
| **P2** | IC 改造文档归档（2 个） | 移动到已有归档目录 | 低（5 分钟） |
| **P3** | 缺失基线文档（5 个） | 自动合并（无冲突） | 零 |

**建议操作顺序：**

1. **在 d1-research 分支上执行：** `git merge develop`
   - 自动合并缺失的治理基线文档（P3）
   - 自动合并分支任务文档更新
   - 遇到入口文档冲突（P0）→ 进入步骤 2

2. **人工解决入口文档冲突（P0）：**
   - `docs/README.md`：保留 develop 结构，补充 1d_experiment_protocol 索引
   - `docs/research/README.md`：保留 develop 结构，补充 1d 专属文档索引
   - `docs/modules/README.md`：保留 develop 版本
   - `docs/overview/README.md`：保留 develop 版本
   - `docs/branch_tasks/README.md`：保留 develop 版本

3. **在 develop 上吸收 1d 专属文档（P1）：**
   - 合并后切到 develop
   - 挑选吸收：1d_experiment_protocol, 1d_research_plan, daily_cs_eval
   - 更新 research/README.md 索引

4. **IC 改造文档归档（P2）：**
   - 移动到 `docs/archive/ic_reform_completed_20260305/`

---

### 2.2 feature/execution-layer-v2

**总体差异：** 30+ 个文档文件差异

**分类统计：**

| 类型 | 数量 | 说明 |
|------|------|------|
| 缺失治理基线文档 | 5 | 与 d1-research 完全一致 |
| 入口文档冲突 | 5 | 与 d1-research 完全一致 |
| 分支任务文档过时 | 4 | 与 d1-research 完全一致 |
| execution 专属文档 | 2 | working_memory（应归档）, branch_plan（应吸收） |
| Archive 差异 | 6 | 与 d1-research 完全一致 |

**优先级排序：**

| 优先级 | 冲突类型 | 处理策略 | 预估工作量 |
|--------|---------|---------|-----------|
| **P0** | 入口文档冲突（5 个） | 人工三方合并 | 低（与 d1 策略相同） |
| **P1** | working_memory 归档 | 按 G1 § 3.1 流程 | 低（10 分钟） |
| **P2** | branch_plan 吸收 | 提炼稳定设计 | 中等（需人工审核） |
| **P3** | 缺失基线文档（5 个） | 自动合并 | 零 |

**建议操作顺序：**

1. **在 execution-layer-v2 分支上执行：** `git merge develop`
2. **人工解决入口文档冲突（P0）：** 策略同 d1-research
3. **Working Memory 归档（P1）：**
   ```bash
   mkdir -p docs/archive/execution_layer_v2_20260311/
   mv docs/modules/execution_layer_working_memory.md docs/archive/execution_layer_v2_20260311/
   echo "# Execution Layer V2 Working Memory Archive" > docs/archive/execution_layer_v2_20260311/README.md
   ```
4. **稳定设计文档吸收（P2）：** 按 G1 § 3.1 文档/方案吸收 Checklist 执行

---

### 2.3 feature/model-3d-5d-10d-head

**总体差异：** 24 个文档文件差异

**分类统计：**

| 类型 | 数量 | 说明 |
|------|------|------|
| 缺失治理基线文档 | 5 | 与前两个分支完全一致 |
| 入口文档冲突 | 5 | 与前两个分支完全一致 |
| 分支任务文档过时 | 4 | 与前两个分支完全一致 |
| Archive 差异 | 6 | 与前两个分支完全一致 |
| 其他文档 | 4 | future_roadmap, topic_maps 等 |

**特殊情况：** 代码已合并到 develop，分支未快进。

**建议：**

**选项 A：快进分支（推荐）**
```bash
git checkout feature/model-3d-5d-10d-head
git merge --ff-only develop  # 应该可以快进
```

**选项 B：直接删除分支**
```bash
git branch -d feature/model-3d-5d-10d-head  # 代码已在 develop
```

**选项 C：保留分支但标记归档**
- 在 `docs/branch_tasks/feature_model_3d_5d_10d_head.md` 标注"已归档"
- 分支不再推进，仅作历史记录

---

## 3. 冲突合并策略矩阵

### 3.1 入口文档合并策略

基于 G2 doc_lifecycle_rules § 4（入口文档集中制）：

| 冲突文件 | 合并策略 | 执行方式 |
|---------|---------|---------|
| docs/README.md | 保留 develop 结构 + 补充分支新增索引 | 三方合并 |
| docs/research/README.md | 保留 develop 结构 + 补充分支新增索引 | 三方合并 |
| docs/modules/README.md | 完全保留 develop | 取 develop |
| docs/overview/README.md | 完全保留 develop | 取 develop |
| docs/branch_tasks/README.md | 完全保留 develop | 取 develop |

**三方合并模板（docs/README.md）：**
```markdown
# develop 版本的导航结构（保留）
1. 项目级入口 A
2. 项目级入口 B
3. 项目级入口 C

# 补充分支新增索引（吸收）
4. [分支新增文档](path/to/new_doc.md)

# develop 版本的描述性文字（保留）
原因是当前真正需要先读清楚的，不只是目录结构，而是：
...（保留 develop 描述）

# 分支新增描述（删除，入口文档不承载细节）
```

---

### 3.2 研究文档吸收策略

基于 G1 § 3（研究结论吸收 Checklist）：

| 文档 | 吸收判断 | 吸收策略 |
|------|---------|---------|
| 1d_experiment_protocol.md | ✅ 稳定协议，已被 G3/G4 引用 | 直接合入，补索引 |
| 1d_research_plan.md | ✅ 稳定计划 | 直接合入，补索引 |
| daily_cs_eval_workflow.md | ✅ 稳定流程 | 直接合入，补索引 |
| IC 改造清单/Prompt 包 | ❌ 专项已完成 | 归档到 archive/ic_reform_completed_20260305/ |
| execution_layer_working_memory.md | ❌ Working Memory | 归档到 archive/execution_layer_v2_20260311/ |
| execution_layer_branch_plan.md | ⚠️ 需审核 | 按 G1 § 3.1 提炼后吸收 |

---

### 3.3 自动合并项

以下文档可自动合并，无需人工干预：

| 类型 | 文件数 | 说明 |
|------|-------|------|
| 治理基线文档 | 5 | develop 单向新增，分支无 |
| G1 验证归档 | 6 | develop 单向新增，分支无 |
| 分支任务文档 | 4 | develop 单向更新，分支无冲突 |

---

## 4. 合并执行计划

### 4.1 合并前准备（在 develop 上）

- [x] 确认治理期闭合 commit 已提交（`f129efe`）
- [ ] 备份当前 develop 分支（可选）
- [ ] 确认所有分支的远程同步状态

---

### 4.2 d1-research 合并执行计划

**阶段 1：在分支上合并 develop**

```bash
# 1. 切换到 d1-research 分支
git checkout feature/model-d1-research

# 2. 合并 develop（会遇到入口文档冲突）
git merge develop

# 3. 解决入口文档冲突（5 个文件）
# - docs/README.md: 三方合并（保留 develop 结构 + 补充 1d 索引）
# - docs/research/README.md: 三方合并
# - docs/modules/README.md: 取 develop
# - docs/overview/README.md: 取 develop
# - docs/branch_tasks/README.md: 取 develop

git checkout --ours docs/modules/README.md
git checkout --ours docs/overview/README.md
git checkout --ours docs/branch_tasks/README.md

# 手工编辑 docs/README.md 和 docs/research/README.md
# （参考 § 3.1 三方合并模板）

git add docs/**/*.md
git commit -m "merge: resolve docs conflicts with develop (preserve develop structure, add 1d indexes)"
```

**阶段 2：在分支上归档 IC 改造文档**

```bash
# 仍在 feature/model-d1-research 分支
mv "docs/research/IC评估体系最小改造清单与计划.md" docs/archive/ic_reform_completed_20260305/
mv "docs/research/IC评估体系改造Prompt包.md" docs/archive/ic_reform_completed_20260305/

# 更新 research/README.md，移除这两个文档的索引
# （编辑文件）

git add -A
git commit -m "archive: IC reform docs to archive/ic_reform_completed_20260305/"
```

**阶段 3：切回 develop，吸收 1d 专属文档**

```bash
# 切回 develop
git checkout develop

# 合并 d1-research 分支（此时已解决冲突）
git merge feature/model-d1-research

# 检查合并结果
git log --oneline -5
git diff HEAD~1 -- docs/
```

---

### 4.3 execution-layer-v2 合并执行计划

**阶段 1：在分支上合并 develop**

```bash
git checkout feature/execution-layer-v2
git merge develop

# 解决入口文档冲突（策略同 d1-research）
git checkout --ours docs/modules/README.md
git checkout --ours docs/overview/README.md
git checkout --ours docs/branch_tasks/README.md

# 手工编辑 docs/README.md 和 docs/research/README.md

git add docs/**/*.md
git commit -m "merge: resolve docs conflicts with develop"
```

**阶段 2：归档 Working Memory**

```bash
mkdir -p docs/archive/execution_layer_v2_20260311/
mv docs/modules/execution_layer_working_memory.md docs/archive/execution_layer_v2_20260311/
echo "# Execution Layer V2 Working Memory Archive

本目录归档 feature/execution-layer-v2 分支的 Working Memory 文档。

**归档时间：** 2026-03-11
**归档原因：** 分支合入 develop 前，按 G1 § 3.1 规则归档过程型工作记忆

**文件清单：**
- execution_layer_working_memory.md：执行层设计过程记录

**稳定设计提炼：** 见 docs/modules/execution_layer_branch_plan_20260309.md
" > docs/archive/execution_layer_v2_20260311/README.md

git add -A
git commit -m "archive: execution-layer-v2 working memory"
```

**阶段 3：稳定设计文档审核与吸收**

```bash
# 按 G1 § 3.1 文档/方案吸收 Checklist 审核
# - 读取 execution_layer_branch_plan_20260309.md
# - 判断哪些是稳定设计、哪些是 working memory
# - 提炼稳定部分到 overview/modules 层
# （需人工审核，此处不自动执行）
```

---

### 4.4 3d-5d-10d-head 处理计划

**推荐：快进分支到 develop**

```bash
git checkout feature/model-3d-5d-10d-head
git merge --ff-only develop

# 如果快进成功
git push origin feature/model-3d-5d-10d-head

# 如果不需要保留分支，可删除
git branch -d feature/model-3d-5d-10d-head
git push origin --delete feature/model-3d-5d-10d-head
```

---

## 5. 合并验证清单

### 5.1 合并后必须检查

- [ ] 所有入口文档（README.md 族）只有导航内容，无长文本描述
- [ ] 治理基线文档（G1/G2/G3/G4 产出）在分支中已存在
- [ ] 分支任务文档已同步 develop 的更新
- [ ] Working Memory 文档已归档
- [ ] 专项完成文档（IC 改造）已归档
- [ ] 稳定研究文档已合入并更新索引

### 5.2 合并后建议运行

```bash
# 检查文档一致性
git diff develop feature/model-d1-research -- docs/overview/*.md
git diff develop feature/execution-layer-v2 -- docs/overview/*.md

# 检查 INVENTORY.md 是否需要更新
ls -la docs/**/*.md | wc -l  # 应与 INVENTORY.md 记录一致

# 运行测试（如有）
pytest tests/
```

---

## 6. 风险与注意事项

### 6.1 入口文档冲突风险

**风险：** 三方合并时可能误删有价值的索引条目

**缓解措施：**
- 合并前备份分支当前 README.md 内容
- 合并后逐行对比，确保新增索引已补充
- 使用 `git diff HEAD~1 -- docs/README.md` 检查合并结果

### 6.2 Working Memory 误判风险

**风险：** 将稳定设计误归档为 Working Memory

**缓解措施：**
- 严格按 G1 § 3.1 的区分标准判断
- 不确定时，保留在原位置，标注"待审核"
- 执行层 branch_plan 需人工审核后再决定

### 6.3 索引过时风险

**风险：** 合并后 README.md 索引指向已归档文档

**缓解措施：**
- 归档文档后立即更新对应 README.md
- 合并后运行 `grep -r "IC评估体系" docs/` 确认无遗留引用

---

## 7. 后续建议

### 7.1 分支合并后的清理

- [ ] 已合并分支是否删除或归档（3d-5d-10d-head 建议删除）
- [ ] 远程分支是否同步删除
- [ ] 本地 worktree 是否清理

### 7.2 入口文档集中制执行

- [ ] 后续所有分支不再修改入口文档
- [ ] 新增文档时在分支任务文档中记录"需补充索引"
- [ ] 合入时由 develop 统一处理入口文档更新

### 7.3 文档治理持续改进

- [ ] 定期检查 INVENTORY.md 与实际文件一致性
- [ ] 定期审查 stale 文档，执行归档
- [ ] 下一次分支合入时验证 G1/G2 规则有效性

---

## 8. 关联文档

- [merge_audit_checklist_20260311.md](merge_audit_checklist_20260311.md)（G1）
- [doc_lifecycle_rules_20260311.md](doc_lifecycle_rules_20260311.md)（G2）
- [shared_layer_inventory_20260311.md](shared_layer_inventory_20260311.md)（G3）
- [config_and_artifact_naming_20260311.md](config_and_artifact_naming_20260311.md)（G4）
- [develop_governance_backlog_20260311.md](../branch_tasks/develop_governance_backlog_20260311.md)（治理总清单）
