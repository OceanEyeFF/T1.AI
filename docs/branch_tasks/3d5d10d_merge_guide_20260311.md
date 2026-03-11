# `feature/model-3d-5d-10d-head` 合并指南（2026-03-11）

## 0. 文档用途

本文档是 `feature/model-3d-5d-10d-head` 分支处理的专属操作指南。

**完整冲突分析报告：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)

---

## 1. 分支概况

**分支名称：** `feature/model-3d-5d-10d-head`
**分支角色：** 主模型线（代码已合并到 develop，分支未快进）
**文档差异：** 24 个文档文件
**预估处理时间：** 5 分钟

---

## 2. 特殊情况说明

**关键事实：**
- ✅ 代码已在 2026-03-11 合并到 develop
- ✅ 测试已通过（`test_trade_like_panel.py` 等）
- ⚠️ 分支未快进到最新 develop
- ⚠️ 分支缺少治理期产出的 4 个核心文档

**文档差异与 d1-research / execution-layer-v2 完全一致：**
- 缺失治理基线文档（5 个）
- 入口文档冲突（5 个）
- 分支任务文档过时（4 个）
- Archive 差异（6 个）

**但无需人工解决冲突，因为：**
- 分支应该可以快进（fast-forward）到 develop
- 代码已在 develop，无新增代码冲突

---

## 3. 推荐处理方案

### 方案 A：快进分支到 develop（推荐 ⭐）

**适用场景：** 希望保留分支引用，但让分支指向最新 develop

```bash
# 1. 切换到 3d-5d-10d-head 分支
git checkout feature/model-3d-5d-10d-head

# 2. 快进合并 develop
git merge --ff-only develop

# 预期输出：
# Updating {old_commit}..{new_commit}
# Fast-forward
#  docs/overview/merge_audit_checklist_20260311.md | 782 ++++++++++++++++++++
#  ... (自动合并所有文档差异)

# 3. 推送到远程（如果需要）
git push origin feature/model-3d-5d-10d-head

# 完成时间：< 1 分钟
```

**验证：**

```bash
# 检查分支是否与 develop 完全一致
git diff develop
# 应该无输出（分支与 develop 一致）

# 检查 git log
git log --oneline -5
# 应该看到治理期的 commit（f129efe, 25271f7）
```

---

### 方案 B：直接删除分支

**适用场景：** 代码已在 develop，不需要保留分支引用

```bash
# 1. 确认当前在 develop 分支
git checkout develop

# 2. 删除本地分支
git branch -d feature/model-3d-5d-10d-head

# 如果提示未合并，强制删除（确认代码已在 develop 后）
git branch -D feature/model-3d-5d-10d-head

# 3. 删除远程分支（需确认，慎重操作）
git push origin --delete feature/model-3d-5d-10d-head

# 完成时间：< 1 分钟
```

**注意：** 远程删除前，请确认团队其他成员不依赖此分支。

---

### 方案 C：保留分支但标记归档

**适用场景：** 需要保留分支作为历史记录

```bash
# 1. 快进分支到 develop（同方案 A）
git checkout feature/model-3d-5d-10d-head
git merge --ff-only develop

# 2. 在分支任务文档中标注"已归档"
# （develop 已在 feature_model_3d_5d_10d_head.md 中标记 frozen）

# 3. 不推送到远程，仅作本地历史记录
# （不执行 git push）

# 完成时间：< 1 分钟
```

---

## 4. 推荐方案：方案 A（快进）

**理由：**
1. ✅ 保留分支引用，便于追溯
2. ✅ 分支自动获得治理期的所有文档
3. ✅ 无需人工解决冲突
4. ✅ 操作最安全（可回退）

**执行步骤（完整）：**

```bash
# Step 1: 切换到分支
git checkout feature/model-3d-5d-10d-head

# Step 2: 快进合并
git merge --ff-only develop

# Step 3: 验证结果
git diff develop  # 应该无输出

git log --oneline -3  # 应该看到：
# 25271f7 docs(governance): add branch baseline conflict analysis report
# f129efe docs(governance): complete develop governance phase - G1/G2/G3/G4
# ... (更早的 commit)

# Step 4: 检查治理基线文档
ls -la docs/overview/merge_audit_checklist_20260311.md
ls -la docs/overview/doc_lifecycle_rules_20260311.md
ls -la docs/overview/shared_layer_inventory_20260311.md
ls -la docs/overview/config_and_artifact_naming_20260311.md
# 应该全部存在

# Step 5: 推送到远程（可选）
git push origin feature/model-3d-5d-10d-head
```

---

## 5. 验证清单

快进完成后，逐项检查：

- [ ] 分支与 develop 完全一致
  ```bash
  git diff develop
  # 无输出 = 一致
  ```

- [ ] 治理基线文档已存在
  ```bash
  ls -la docs/overview/{merge_audit_checklist,doc_lifecycle_rules,shared_layer_inventory,config_and_artifact_naming}_20260311.md
  # 应该显示 4 个文件
  ```

- [ ] 分支任务文档已更新（frozen 标记）
  ```bash
  grep "frozen" docs/branch_tasks/feature_model_3d_5d_10d_head.md
  # 应该找到 frozen 状态标记
  ```

- [ ] INVENTORY.md 已包含新增文档
  ```bash
  grep "branch_baseline_conflict_analysis" docs/INVENTORY.md
  # 应该找到冲突分析文档条目
  ```

- [ ] git log 包含治理期 commit
  ```bash
  git log --oneline --grep="governance" -3
  # 应该看到 f129efe 和 25271f7
  ```

---

## 6. 如果快进失败

**现象：** 执行 `git merge --ff-only develop` 时提示：

```
fatal: Not possible to fast-forward, aborting.
```

**原因：** 分支有 develop 没有的 commit

**处理方式：**

```bash
# 查看分支独有的 commit
git log develop..feature/model-3d-5d-10d-head --oneline

# 选项 1：如果分支有有价值的 commit，需要普通合并
git merge develop  # 不使用 --ff-only

# 选项 2：如果分支 commit 已无价值，强制快进
git reset --hard develop
git push origin feature/model-3d-5d-10d-head --force  # 慎重操作
```

**建议：** 快进失败时，联系原分支维护者确认处理方式。

---

## 7. 完成后状态

**分支状态：**
- `feature/model-3d-5d-10d-head` 与 `develop` 完全一致
- 分支指向最新的治理期 commit（25271f7）
- 分支任务文档标记为 `frozen`

**可选清理：**

```bash
# 如果不再需要分支，可以删除
git branch -d feature/model-3d-5d-10d-head  # 本地
git push origin --delete feature/model-3d-5d-10d-head  # 远程（慎重）

# 或者保留作为历史记录
# （不删除，但不再推进工作）
```

---

## 8. 关联文档

- **完整冲突分析：** [../overview/branch_baseline_conflict_analysis_20260311.md](../overview/branch_baseline_conflict_analysis_20260311.md)
- **分支任务文档：** [feature_model_3d_5d_10d_head.md](feature_model_3d_5d_10d_head.md)
- **治理期总结：** [develop.md](develop.md) § 治理期总结
