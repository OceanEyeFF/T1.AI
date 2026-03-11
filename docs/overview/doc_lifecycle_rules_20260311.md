# 文档生命周期规则（2026-03-11）

## 1. 目的

本文档定义仓库文档的归档流程、入口文档修改权限和维护责任矩阵。

与 [doc_governance.md](doc_governance.md) 的关系：
- `doc_governance.md` 负责：命名规则、颗粒度分类、时间属性
- 本文档负责：生命周期管理、归档流程、权限规则、维护职责

---

## 2. 文档状态定义

每个文档必须处于以下四种状态之一：

| 状态 | 含义 | 允许修改 | INVENTORY 标记 |
|------|------|----------|----------------|
| `active` | 正在使用的基线文档 | 是 | `active` |
| `frozen` | 已冻结的快照，不应修改 | 否（需新建替代文档） | `frozen` |
| `stale` | 可能过期，需确认是否归档 | 仅限状态更新 | `stale` |
| `archived` | 已移入 `archive/`，不再是活跃入口 | 否 | `archived` |

### 状态流转规则

```
active → frozen   （结论已冻结、快照已保存）
active → stale    （内容可能过期、被新文档取代）
stale  → archived （确认过期后归档）
stale  → active   （重新确认仍然有效）
frozen → archived （冻结文档不再需要保留在活跃目录时）
```

**禁止流转：**
- `archived → active`（不允许把已归档文档重新激活，应新建文档）
- 直接从 `active` 跳到 `archived`（必须经过 `stale` 确认）

---

## 3. 归档流程

### 3.1 归档触发条件

以下任一条件满足时，应将文档标记为 `stale` 并启动归档评估：

1. **分支已合并/归档**：对应分支的代码已合入 develop，分支进入归档状态
2. **方案已废弃**：设计方案被新方案取代，旧方案不再作为实施依据
3. **结论已提炼**：研究结论已提炼到更高层级文档（overview/modules/interfaces）
4. **专项已完成**：专项任务（如 IC 改造、G1 验证）已全部完成
5. **时效已过**：带日期的短期文档超过其预期有效期

### 3.2 归档目标位置

```
docs/archive/
├── long_term/       # 仍有参考价值的历史资料
├── short_term/      # 已下线的短期材料
├── {topic}_{date}/  # 专项归档目录（如 g1_validation_20260311/）
└── README.md        # 归档索引
```

**归档子目录选择规则：**
- 完成的专项任务 → 以 `{topic}_{date}/` 命名的专属目录
- 被取代的研究文档 → `long_term/`（仍有参考价值）或 `short_term/`（无参考价值）
- 过期的执行性文档 → `short_term/`

### 3.3 归档动作（按顺序执行）

1. **确认归档**：在文档头部或任务文档中标注归档原因
2. **物理移动**：将文件移入 `docs/archive/` 对应子目录
3. **更新索引**：
   - 更新 `docs/INVENTORY.md` 中的状态标记
   - 更新 `docs/archive/README.md` 的归档索引
   - 更新原所在目录的 `README.md`（移除该文档的引用）
4. **留 redirect 说明**（可选）：如果文档被频繁引用，在原位置留一行说明指向新位置

### 3.4 归档审查周期

- 每次治理专题完成后，顺带检查是否有新的 `stale` 文档
- 每次分支合入 develop 后，检查对应分支的任务文档和过程文档
- 不做定期批量归档（避免形式主义），按事件驱动

---

## 4. 入口文档修改权限规则

### 4.1 总规则：严格集中制

所有入口文档（README.md 族）的修改权只在 `develop` 分支上行使。

功能/研究分支如需变更入口文档，必须：
1. 在该分支的任务文档（`branch_tasks/`）中记录变更诉求
2. 等合入 `develop` 时，由 develop 统一处理入口文档更新
3. 不在功能分支上直接修改任何入口文档

### 4.2 入口文档清单

以下文件受集中制约束：

**项目根目录：**
- `README.md`
- `NEXT_STEPS.md`
- `ROADMAP.md`

**docs/ 根：**
- `docs/README.md`
- `docs/INVENTORY.md`

**各层 README：**
- `docs/overview/README.md`
- `docs/modules/README.md`
- `docs/interfaces/README.md`
- `docs/research/README.md`
- `docs/archive/README.md`
- `docs/branch_tasks/README.md`

### 4.3 例外情况

- `docs/branch_tasks/{branch_name}.md` 不是入口文档，各分支可自行维护
- 如果功能分支新增了一个目录层级的 README（极少见），须在 merge 时通过 G1 checklist 审核

### 4.4 与 G1 Merge/Audit Checklist 的关系

[merge_audit_checklist_20260311.md](merge_audit_checklist_20260311.md) 中的文档入口检查项应引用本规则：
- 代码分支合入时检查：是否修改了入口文档（不应修改）
- 如确需更新入口文档：须在 develop 上单独处理

---

## 5. 维护责任矩阵

### 5.1 按目录分配维护者

| 目录 | 维护分支 | 维护触发 | 归档责任 |
|------|----------|----------|----------|
| `overview/` | develop | 架构/治理变更时 | develop |
| `modules/` | develop（基线文档） / 功能分支（新增模块文档） | 模块边界变更时 | develop |
| `interfaces/` | develop | 协议/字段变更时 | develop |
| `research/` | 对应研究分支 | 实验完成或结论变更时 | develop |
| `branch_tasks/` | 各分支自维护 | 任务状态变更时 | develop |
| `archive/` | develop | 归档动作发生时 | develop |

### 5.2 维护动作标准

**新增文档时，必须同步：**
1. `docs/INVENTORY.md` — 增加条目并标注状态
2. 对应目录的 `README.md` — 增加导航条目

**删除/归档文档时，必须同步：**
1. `docs/INVENTORY.md` — 更新状态标记
2. 对应目录的 `README.md` — 移除导航条目
3. `docs/archive/README.md` — 增加归档说明（如物理移动）

**文档状态变更时（active → frozen 等），必须同步：**
1. `docs/INVENTORY.md` — 更新状态标记

### 5.3 分支任务文档的特殊维护规则

- 活跃分支的任务文档由该分支维护
- 已归档分支的任务文档由 develop 维护其归档状态
- 新分支创建时，必须从模板创建任务文档（模板见本文档 § 6）

---

## 6. 分支任务文档模板

新分支创建任务文档时，至少包含以下结构：

```markdown
# `{branch_name}` 任务文档

## 分支角色

- 角色：{简要描述}
- 当前定位：{研究/功能/方案/收口}

## 当前状态

- [ ] {关键里程碑}

## 当前必须做

- [ ] {具体任务}

## 明确不做

- [ ] {边界约束}

## 退出条件

- [ ] {分支完成的判定标准}
```

---

## 7. 本文档自身的维护规则

- 本文档属于 `overview/` 层，由 develop 分支维护
- 状态：`active`
- 如需修改归档流程或权限规则，应在 develop 上直接更新本文档
- 如果本文档的规则与 `doc_governance.md` 冲突，以本文档为准（生命周期覆盖命名）
