# 全局工作规则

> MS-R2-001 | 2026-06-23 | 维护者：OceanEyeFF

本文档固化了 T1.AI 仓库的全局工作规则。所有开发、实验、文档操作必须遵守。

---

## 1. 三区模型

Repo 目录按流程阶段分为三个互不重叠的区：

| 区 | 语义 | 放什么 | 不放什么 |
|----|------|--------|---------|
| `inputs/` | 输入区 | 数据缓存、选股池、配置档案 | 训练产物、推理输出 |
| `workspace/` | 工作区 | checkpoint、运行日志、registry | 原始数据、最终交付 |
| `outputs/` | 输出区 | 预测、报告、交易信号 | 中间产物、配置 |

**`src/` 是独立代码层，不归入三区。**

违规示例：

- ❌ 把 checkpoint 放在 `outputs/` — checkpoint 是中间产物，应放在 `workspace/checkpoints/`
- ❌ 把数据缓存放在 `workspace/` — 缓存是输入，应放在 `inputs/data/cache/`
- ❌ 把配置文件放在 `src/` — 配置应放在 `inputs/configs/`

---

## 2. X×Y×Z 组合测试流程

### 三维轴

- **X**：选股池（`inputs/pools/`）— 不同的股票代码集合
- **Y**：模型架构（`src/ashare_lab/models/`）— 通过 config 调参适配
- **Z**：配置档案（`inputs/configs/profiles/`）— 输入维度 × 回溯窗口 × 输出 horizon

### 测试步骤

1. **全量扫荡**：`inputs/configs/experiments/` 中定义 X×Y×Z 矩阵，两两组合测试
2. **筛选**：选出 IC 表现最好的配对，记录到 `workspace/registry/certified.json`
3. **滚动重训**：对认证配对每周一次微调，持续验证 IC 稳定性
4. **推理**：认证配对产出定期预测 → `outputs/predictions/`
5. **消费**：交易策略层（Layer 2）只消费认证配对的输出

### 禁止

- ❌ 不使用实验配置定义的矩阵，直接手动调参训练然后声称"最优"
- ❌ 不通过滚动 IC 时间序列验证就声称"模型可用"
- ❌ 不在 `certified.json` 中的模型配对进入推理流水线

---

## 3. 策略自包含规范

每个选股策略一个子文件夹，包含：

```
inputs/pools/<strategy_name>/
├── config.toml          # StockPoolRecord schema（必填）
├── symbols.csv          # 股票列表
└── (optional) metadata.json
```

策略代码放在 `src/ashare_lab/stock_pool/<strategy_name>/strategy.py`，实现 `StockPoolStrategy.select()`。

---

## 4. 模型自包含规范

每个模型一个子文件夹：

```
src/ashare_lab/models/<model_name>/
├── __init__.py          # 实现 ModelABC（必填）
├── config.toml          # 默认超参配置（必填）
└── (optional) _backend.py
```

Checkpoint 保存到 `workspace/checkpoints/<model_name>_<variant>.pt`。

---

## 5. .gitignore 规则

```
inputs/data/cache/       # 数据缓存不跟踪
workspace/checkpoints/   # 模型权重不跟踪
workspace/runs/          # 运行日志不跟踪
outputs/predictions/     # 推理输出不跟踪
outputs/reports/         # 评估报告不跟踪
*.pt *.pth *.ckpt        # 全局排除模型文件
```

---

## 6. Commit 与分支策略

- **一个 Milestone 一个独立开发分支**：`milestone/{milestone_id}-{slug}`
- **develop 是程序员审查分支**，Milestone 完成后 merge 到 develop
- **Commit 须经程序员批准**
- **Push 须经程序员批准**
- 禁止 force push、分支删除，禁止对 develop 的直接破坏性变更

---

## 7. 工作流追踪（历史）

原 Harness 分层闭环控制系统的 artifact 目录 `.servo/`（milestone / worktrack / control-state）
已于 2026-08 移除。Milestone 历史不再保留于仓库，工作规划以 `NEXT_STEPS.md` / `ROADMAP.md`
及常规 git 提交历史为准。

---

## 8. 文档规范

- 新文档放入 `docs/` 的对应子目录（architecture/ reference/ guides/ research/）
- 过期文档移入 `docs/archive/`
- 每个空目录必须有 `README.md` 说明其在三区模型中的角色
- 根 `README.md` 是唯一入口，不维护多份重叠的索引

---

## 9. 禁止事项清单

- ❌ 在 `src/` 中硬编码路径字符串（路径从 config 传入或使用相对 PROJECT_ROOT）
- ❌ 在脚本中内联模型定义（模型必须放在 `src/ashare_lab/models/` 下并通过 registry 创建）
- ❌ 在 `outputs/` 存 checkpoint
- ❌ 在 `inputs/` 存训练产物
- ❌ 跨 Milestone 共用分支
- ❌ 未经 pre-milestone intake 直接激活 goal-driven milestone
