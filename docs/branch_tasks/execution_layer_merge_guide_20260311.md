# `feature/execution-layer-v2` 合并指南（2026-03-11）

## 0. 文档用途

本文档是 `feature/execution-layer-v2` 分支合并到 `develop` 的专属操作指南。

**完整冲突分析报告：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)

---

## 1. 分支概况

**分支名称：** `feature/execution-layer-v2`
**分支角色：** 执行层设计线
**文档差异：** 30+ 个文档文件
**预估处理时间：** 40 分钟

---

## 2. 冲突分类统计

| 类型 | 数量 | 处理方式 | 优先级 |
|------|------|---------|--------|
| **缺失治理基线文档** | 5 | 自动合并 | P3（零成本） |
| **入口文档冲突** | 5 | 人工三方合并 | P0（30 分钟） |
| **分支任务文档过时** | 4 | 自动合并 | P3（零成本） |
| **execution 专属文档** | 2 | Working Memory 归档 + 稳定设计审核 | P1/P2（10 分钟） |
| **Archive 差异** | 6 | 自动合并 | P3（零成本） |

---

## 3. 冲突详情

### 3.1 缺失治理基线文档（P3 - 自动合并）

**现象：** 与 d1-research 分支完全一致，缺少治理期产出的 4 个核心文档

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

**合并策略：** 与 d1-research 完全一致

| 文件 | 冲突类型 | 合并策略 |
|------|---------|---------|
| `docs/README.md` | 新增执行层文档索引 | **三方合并** |
| `docs/research/README.md` | 新增执行层计划索引 | **三方合并** |
| `docs/modules/README.md` | 分支修改 | **完全保留 develop** |
| `docs/overview/README.md` | 分支修改 | **完全保留 develop** |
| `docs/branch_tasks/README.md` | 分支未更新 | **完全保留 develop** |

**合并原则（基于 G2 集中制）：**
- ✅ 保留 develop 的导航结构和描述性文字
- ✅ 补充分支新增的执行层文档索引条目
- ❌ 删除分支对描述性文字的修改

---

### 3.3 execution 专属文档（P1/P2 - 归档或审核）

| 文档 | 状态 | 处理方式 | 优先级 |
|------|------|---------|--------|
| `execution_layer_working_memory.md` | Working Memory | ❌ 应归档（按 G1 § 3.1 规则） | P1 |
| `execution_layer_branch_plan_20260309.md` | 执行层计划 | ⚠️ 需审核（区分稳定设计 vs Working Memory） | P2 |

**Working Memory 归档流程：**
- 归档时机：功能分支提交合并请求前
- 归档路径：`docs/archive/execution_layer_v2_20260311/`
- 归档说明：在归档目录下创建 README.md

**稳定设计文档审核标准（G1 § 3.1）：**
- 是否具有长期参考价值？
- 是否已被提炼到 overview/modules 层？
- 是否仍包含过程型工作记忆？

---

## 4. 合并执行计划

### 阶段 1：在分支上合并 develop

```bash
# 1. 切换到 execution-layer-v2 分支
git checkout feature/execution-layer-v2

# 2. 合并 develop（会遇到入口文档冲突）
git merge develop

# 预期输出：
# Auto-merging docs/README.md
# CONFLICT (content): Merge conflict in docs/README.md
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

**处理原则：** 与 d1-research 相同
- 保留 develop 的导航结构
- 补充分支新增的执行层文档索引
- 删除分支的描述性文字修改

**手工编辑命令：**

```bash
# 编辑 docs/README.md
vim docs/README.md

# 编辑 docs/research/README.md
vim docs/research/README.md

# 执行三方合并（参考 d1-research 合并模板）
```

#### 步骤 2.3：提交合并结果

```bash
# 添加所有已解决的冲突文件
git add docs/**/*.md

# 提交合并
git commit -m "merge: resolve docs conflicts with develop"
```

---

### 阶段 3：归档 Working Memory（P1）

```bash
# 仍在 feature/execution-layer-v2 分支

# 创建归档目录
mkdir -p docs/archive/execution_layer_v2_20260311/

# 移动 Working Memory 文档
mv docs/modules/execution_layer_working_memory.md \
   docs/archive/execution_layer_v2_20260311/

# 创建归档说明
cat > docs/archive/execution_layer_v2_20260311/README.md <<'EOF'
# Execution Layer V2 Working Memory Archive

本目录归档 `feature/execution-layer-v2` 分支的 Working Memory 文档。

**归档时间：** 2026-03-11
**归档原因：** 分支合入 develop 前，按 G1 § 3.1 规则归档过程型工作记忆

**文件清单：**
- `execution_layer_working_memory.md`：执行层设计过程记录

**稳定设计提炼：** 见 `docs/modules/execution_layer_branch_plan_20260309.md`（需审核）
EOF

# 提交归档
git add -A
git commit -m "archive: execution-layer-v2 working memory"
```

---

### 阶段 4：审核稳定设计文档（P2）

```bash
# 读取 execution_layer_branch_plan_20260309.md
cat docs/modules/execution_layer_branch_plan_20260309.md

# 按 G1 § 3.1 标准判断：
# 1. 是否具有长期参考价值？
# 2. 关键设计是否已提炼到 overview/modules 层？
# 3. 是否仍包含过程型工作记忆？

# 选项 A：如果是稳定设计，保留在原位置
# （无需操作）

# 选项 B：如果是 Working Memory，移入归档
mv docs/modules/execution_layer_branch_plan_20260309.md \
   docs/archive/execution_layer_v2_20260311/

# 选项 C：如果部分稳定，提炼后归档原稿
# （需人工提炼，不在此自动执行）
```

**建议审核标准：**

```markdown
稳定设计的特征：
- 明确的接口定义
- 清晰的架构分层
- 可复用的设计模式
- 技术选型依据

Working Memory 的特征：
- 流水账式的过程记录
- "今天做了什么"式的日志
- 未提炼的讨论记录
- 临时的调试笔记
```

---

### 阶段 5：切回 develop，完成合并

```bash
# 切回 develop
git checkout develop

# 合并 execution-layer-v2 分支（此时已解决所有冲突）
git merge feature/execution-layer-v2

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
  head -30 docs/README.md
  ```

- [ ] Working Memory 文档已归档
  ```bash
  ls -la docs/archive/execution_layer_v2_20260311/execution_layer_working_memory.md
  # 应该显示文件已存在

  ls -la docs/modules/execution_layer_working_memory.md
  # 应该显示：No such file or directory
  ```

- [ ] 归档目录有 README.md 说明
  ```bash
  cat docs/archive/execution_layer_v2_20260311/README.md
  # 应该显示归档说明
  ```

- [ ] 稳定设计文档状态已确认
  ```bash
  ls -la docs/modules/execution_layer_branch_plan_20260309.md
  # 或在 modules/ 或在 archive/，取决于审核结果
  ```

- [ ] 分支任务文档已同步 develop 更新
  ```bash
  grep "G1/G2/G3/G4" docs/branch_tasks/feature_execution_layer_v2.md
  # 应该能找到治理专题引用
  ```

---

## 6. 风险与注意事项

### 6.1 Working Memory 误判风险

**风险：** 将稳定设计误归档为 Working Memory

**缓解措施：**
- 严格按 G1 § 3.1 的区分标准判断
- 不确定时，保留在原位置，标注"待审核"
- `execution_layer_branch_plan_20260309.md` 需人工审核后再决定

**判断清单：**

| 特征 | 稳定设计 | Working Memory |
|------|---------|----------------|
| 接口定义 | ✅ 明确 | ❌ 模糊 |
| 架构分层 | ✅ 清晰 | ❌ 缺失 |
| 可复用性 | ✅ 高 | ❌ 低 |
| 时间属性 | ✅ 长期有效 | ❌ 过程记录 |

### 6.2 归档目录命名

**规范：** `{branch_name}_{YYYYMMDD}/`
- ✅ 正确：`execution_layer_v2_20260311/`
- ❌ 错误：`execution-layer-v2/`（缺日期）
- ❌ 错误：`execution_layer_20260311/`（缺分支版本号）

---

## 7. 完成后清理（可选）

```bash
# 如果不再需要分支（合并后）
git branch -d feature/execution-layer-v2  # 本地删除
git push origin --delete feature/execution-layer-v2  # 远程删除（需确认）
```

---

## 8. 关联文档

- **完整冲突分析：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)
- **G1 § 3.1 Working Memory 归档规则：** [../overview/merge_audit_checklist_20260311.md](../overview/merge_audit_checklist_20260311.md)
- **G2 文档生命周期规则：** [../overview/doc_lifecycle_rules_20260311.md](../overview/doc_lifecycle_rules_20260311.md)
- **分支任务文档：** [feature_execution_layer_v2.md](feature_execution_layer_v2.md)
