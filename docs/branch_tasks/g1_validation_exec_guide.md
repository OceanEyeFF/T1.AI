# G1 验证执行指引（新窗口专用）

> 本文件是 G1 Checklist 验证的单一入口。新窗口打开后只需读这一份文档即可开始工作。

## 背景

我们已经在 `develop` 上创建了 Merge/Audit Checklist，现在需要验证其可操作性。

## 必读文档（按顺序）

1. **本文件** — 执行步骤总览
2. `docs/overview/merge_audit_checklist_20260311.md` — 被验证的 Checklist，重点看 **§3 文档/方案吸收 Checklist**
3. `docs/branch_tasks/feature_execution_layer_v2.md` — 验证对象分支的任务文档
4. `docs/overview/doc_governance.md` — 文档颗粒度规则（验证时需要参照）

## 环境信息

- 当前工作目录：`/home/oceaneye/github/T1.AI`（develop 分支）
- execution-layer-v2 worktree：`/home/oceaneye/github/T1.AI-exec`
- Python 环境：`/home/oceaneye/miniconda3/envs/ashare-lab/bin/python`

## 执行步骤

### Step 1：创建验证分支

```bash
cd /home/oceaneye/github/T1.AI
git checkout develop
git checkout -b feature/g1-validation
```

### Step 2：盘点 execution-layer-v2 的文档变更

```bash
cd /home/oceaneye/github/T1.AI-exec
git diff develop --name-only
```

对每个变更文件（尤其是 docs/ 下的 .md 文件），判断属于哪一类：
- **稳定设计基线**（可吸收进 develop）
- **Working memory**（保留在分支或归档）
- **待重写**（暂不吸收）

已知的分支文档（来自审计结论）：
- `docs/research/execution_layer_branch_plan_20260309.md` → 稳定设计
- `docs/technical/execution_layer_phase_implementation.md` → 稳定设计
- `docs/technical/portfolio_manager_algorithm.md` → 稳定设计
- `docs/technical/phase0_design_research_single_score_input.md` → 稳定设计
- `docs/modules/execution_layer_working_memory.md` → Working memory

### Step 3：填写自查表

在 `feature/g1-validation` 分支上创建：`validation_artifacts/execution_layer_v2_self_check.md`

按照 `merge_audit_checklist_20260311.md` §3 的模板填写，核心关注：
- 每个检查项是否能快速判断 Yes/No
- 是否有"不知道怎么判断"的情况
- 文档分类是否有边界模糊的案例

### Step 4：模拟 develop 维护者复核

换一个视角，假装自己是 develop 维护者，复核 Step 3 的自查表：
- 自查表的结论是否可信
- 是否需要进一步确认
- 判断标准是否足够客观

创建复核记录：`validation_artifacts/develop_reviewer_notes.md`

### Step 5：汇总问题

创建问题汇总：`validation_artifacts/g1_validation_findings.md`

记录：
- 哪些检查项清晰好用
- 哪些检查项有歧义或难以判断
- 对 checklist 的具体改进建议
- 双重验证流程是否顺畅

### Step 6：归档并清理

```bash
cd /home/oceaneye/github/T1.AI
git checkout feature/g1-validation

# 将验证产物归档
mkdir -p docs/archive/g1_validation_20260311
cp validation_artifacts/* docs/archive/g1_validation_20260311/
git add docs/archive/g1_validation_20260311/
git commit -m "archive: G1 checklist validation artifacts"

# 如果 checklist 需要修改，在 develop 上修改
git checkout develop
# （根据验证发现修改 merge_audit_checklist_20260311.md）

# 删除验证分支
git branch -D feature/g1-validation
```

## 验证成功标准

- **通过**：所有检查项清晰无歧义，或仅有 ≤3 个小问题且已修正
- **需再次验证**：>3 个问题，checklist 需大幅改进

## 产出物清单

验证完成后应产出：
1. `validation_artifacts/execution_layer_v2_self_check.md` — 填好的自查表
2. `validation_artifacts/develop_reviewer_notes.md` — 复核记录
3. `validation_artifacts/g1_validation_findings.md` — 问题汇总与改进建议
4. 如有修改：更新后的 `docs/overview/merge_audit_checklist_20260311.md`

## 完成后回到原窗口

验证完成后，回到原来的对话窗口，告知验证结果和发现的问题。
原窗口会据此更新 `develop_governance_backlog_20260311.md` 中 G1 的验证状态。
