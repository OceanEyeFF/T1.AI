---
title: "MS-R2-001 Pre-Milestone Intake Review"
artifact_type: "pre-milestone-intake-review"
milestone_id: "MS-R2-001"
updated: "2026-06-23T01:00:00+08:00"
updated_by: "codex"
---

# MS-R2-001 Pre-Milestone Intake Review

## Intake Status

- intake_status: ready
- request_summary: >
  Programmer 提出 Repo 目录排布应从"探索期多线并行"收敛为以 `src/` 为核心、
  `inputs/ → workspace/ → outputs/` 三区清晰分层的稳定布局，
  服务于 X×Y×Z 组合测试矩阵 + 滚动重训验证的核心工作流。
  已确认：3区模型 + src/独立 + experiments/归入 inputs/configs/ + 最激进清理（老产物直接删除）。
- programmer_confirmed: true
- ready_for_init_milestone: true
- intake_skipped: false
- residual_risk_accepted: true
- accepted_residual_risk: >
  旧 checkpoint（models/*.pt）、*smoke** 数据集、output/recommendations/ 历史 JSON
  基于 AkShare 数据构建，TuShare 数据更准确，直接删除不归档。
  daily_pipeline.py 对 models/latest_mtl.pt 的硬编码引用需在 Worktrack 中处理。

## Request Summary

Programmer 的核心诉求分两个层次：

**层次 1：目录排布问题**

当前 21 个一级目录是探索期多线并行时代的遗留，`src/ashare_lab/` 已成为训练流水线主体后，外围目录没有同步收束。`experiments/`、`logs/`、`models/` 等一级目录要么是历史残留，要么与 `src/` 内的同名模块产生概念冲突。

**层次 2：流程架构认知**

Programmer 的实际工作流不是"研究→生产"两天线，而是一个 **X×Y×Z 组合测试矩阵 + 滚动重训验证** 的闭环：

```
X: 选股池（不同策略 → 不同股票代码集合）
Y: 模型架构（LSTM / XGBoost / Transformer，通过 config 调参适配）
Z: 配置档案（输入维度 × 回溯窗口 × 输出 horizon）

全量训练测试 (X×Y×Z) → 筛选最佳配对 → 认证注册
                                          ↓
                                    每周滚动重训
                                          ↓
                                    IC 时间序列验证
                                          ↓
                                    定期推理产出
                                          ↓
                                    交易策略层消费
```

这个闭环的产物分两路：

- **Layer 1（当前主体）**：模型验证层 — 滚动重训 → IC 稳定性评估 → 选模决策
- **Layer 2（后续）**：交易策略层 — 消费 Layer 1 的预测 → 模拟盘回测 → 实盘记录

目录设计应明确服务于 Layer 1 的 `X×Y×Z → 训练 → IC验证 → 认证` 循环。

**已确认的关键决策**：

- 采用 **3 区模型**：`inputs/`（输入区）→ `workspace/`（工作区）→ `outputs/`（输出区）
- `src/` 作为代码层 **独立一级目录**，不归入三区
- `experiments/`（实验矩阵定义）放入 `inputs/configs/`
- Milestone 范围：**只做目录重组**，TuShare 数据湖构建留给后续 Milestone
- 老 AkShare 产物标记 deprecated，不迁移

## Observed Facts

### 当前根目录结构

```
一级目录 (21):
  configs/      13 files    yaml/toml 配置 + datasets/ experiments/ stock_pools/
  data/         1007 files  cache/(~990 csv) + datasets/(34 _smoke_*)
  deployment/   3 files     crontab + systemd
  docs/         73 files    archive/ branch_tasks/ interfaces/ modules/ overview/ research/
  experiments/  1 file      XGBoost_pool_comparison/experiment_design.md
  logs/         1 file      mtl_train_log.csv
  models/       3 items     best_mtl.pt, latest_mtl.pt, rolling_dim19/
  output/       48 files    datasets/ recommendations/ reports/
  scripts/      78 files    36 入口脚本 + __pycache__/
  src/          218 files   ashare_lab/ 主包
  tests/        210 files   46 test_*.py
  ... + .servo/ .git/ .agents/ .claude/ + 根 .md/.toml/.yml

根文件 (9):
  CLAUDE.md  NEXT_STEPS.md  README.md  ROADMAP.md
  environment.yml  pyproject.toml  requirements.txt  requirements-dev.txt
```

### 流程架构事实

1. **数据源**：`src/ashare_lab/data/` — AkShare（当前主力缓存 ~990 csv）、TuShare、ODP 三适配器。TuShare 数据更准确，programmer 计划以 TuShare 为主。
2. **选股池**：`src/ashare_lab/stock_pool/` — 已收敛为 StockPoolStrategy ABC + low_manipulation 策略。输出股票代码集合。
3. **数据集构建**：`src/ashare_lab/dataset/` — SequenceBuilder + MarketStateBuilder。消费 `data/cache/` 中的日K CSV。
4. **模型代码**：`src/ashare_lab/models/` — 已收敛为 ModelABC + registry（Transformer/LSTM/XGBoost）。
5. **训练器**：`src/ashare_lab/training/trainer.py` — TrainerConfig（batch/lr/patience/scheduler），checkpoint 保存到 `runs/checkpoints/`。
6. **评估**：`src/ashare_lab/evaluation/` — IC/RankIC/月分布/hit rate。
7. **日频流水线**：`src/ashare_lab/pipeline/orchestrator/` — 5 阶段（data_refresh→recommendation→persistence→validation→record）。
8. **推荐引擎**：`src/ashare_lab/recommendation/` — RecommendationEngine（Top-N）+ History（SQLite）+ Validator。
9. **回测**：`src/ashare_lab/backtest/` — BacktestEngine（T+1/涨跌停）。

### 路径硬编码热点

- `scripts/daily_pipeline.py`: `configs/pipeline.yaml`, `configs/data_source.yaml`, `models/latest_mtl.pt`, `configs/model_mtl.yaml` — 全部相对 PROJECT_ROOT
- `configs/pipeline.yaml`: `recommendation_dir: "data/recommendations"`, `report_dir: "data/recommendations/validation"`, `db_path: "data/recommendations.db"`, `run_meta_path: "logs/pipeline_runs.jsonl"`, 日志 `file: "logs/pipeline.log"`
- `configs/data_source.yaml`: `cache_dir: "data/cache"`
- `src/ashare_lab/training/trainer.py`: `save_dir: Path("runs/checkpoints")`
- `src/ashare_lab/pipeline/orchestrator/core.py`: `_PipelineSettings` dataclass 默认值引用 `data/recommendations`, `data/recommendations.db`, `logs/pipeline_runs.jsonl`

## Inferred Assumptions

1. `src/ashare_lab/` 内部模块分层正确，本 Milestone 不动内部结构。
2. `data/cache/` 中 ~990 个 AkShare CSV 暂时保留（TuShare 迁移是后续 Milestone），但标记为 deprecated。
3. `scripts/` 中 36 个入口脚本的归类（build/train/eval/run）可以推迟到后续 Milestone，本轮只修路径。
4. `tests/` 结构对应 `src/`，不需要调整。
5. 根 .md/.toml/.yml 文件保留，符合 Python 项目惯例。
6. `deployment/` 保留为 systemd/crontab 配置目录，不归入三区。
7. `.gitignore` 已排除 `*.pt *.pth *.ckpt`，重组后需确认新位置被覆盖。

## Programmer Decisions Confirmed

| 决策 | 结论 |
|------|------|
| 一级目录模型 | **3 区模型**：`inputs/` `workspace/` `outputs/` + 独立 `src/` |
| src/ 归属 | **独立一级目录**，不归入三区 |
| experiments/ 位置 | 放入 `inputs/configs/experiments/`（实验矩阵定义是输入参数） |
| Milestone 范围 | 只做目录重组，不包含 TuShare 数据迁移 |
| TuShare 迁移 | 后续独立 Milestone |

## Target Directory Layout

### 收敛后一级目录（21 → 10）

```
T1.AI/
│
├── inputs/                         # ═══ Zone 1: 输入区 ═══
│   ├── data/                       # 数据湖
│   │   ├── cache/                  #   日K缓存（当前 AkShare ~990 csv → 后续 TuShare）
│   │   └── derived/                #   高阶衍生特征（动量/波动率等）
│   ├── pools/                      # X 轴：选股池定义
│   │   ├── low_manipulation/       #   strategy.py + config.toml + symbols.csv
│   │   ├── momentum/
│   │   └── value/
│   └── configs/                    # Z 轴：配置档案
│       ├── profiles/               #   输入维度 × 输出 horizon 组合
│       ├── experiments/            #   X×Y×Z 实验矩阵定义（全量扫荡/迭代训练）
│       ├── pipeline.toml           #   日频流水线配置
│       └── data_source.toml        #   数据源配置
│
├── src/                            # Y 轴：模型代码（独立一级）
│   └── ashare_lab/                 #   内部结构不动
│       ├── data/                   #   数据适配器
│       ├── stock_pool/             #   选股策略（已收敛）
│       ├── dataset/                #   数据集构建
│       ├── features/ / labels/     #   特征+标签
│       ├── models/                 #   模型架构（已收敛）
│       ├── training/ / evaluation/ #   训练+评估
│       ├── pipeline/               #   日频流水线
│       ├── recommendation/         #   推荐引擎
│       └── backtest/               #   回测
│
├── workspace/                      # ═══ Zone 2: 工作区 ═══
│   ├── checkpoints/                #   训练产出的模型权重
│   ├── runs/                       #   实验运行日志
│   └── registry/                   #   配对认证注册表
│       └── certified.json          #   {pair_id: {pool, model, config, ckpt, ic_series}}
│
├── outputs/                        # ═══ Zone 3: 输出区（交易层消费面）═══
│   ├── predictions/                #   定期推理输出
│   ├── reports/                    #   IC 时间序列 + 评估报告
│   └── signals/                    #   （后续）交易策略层输入
│
├── scripts/                        # 入口脚本
├── tests/                          # 测试
├── docs/                           # 文档（扁平化）
├── deployment/                     # systemd/crontab
├── .servo/                         # Harness 控制面
│
├── pyproject.toml                  # Python 项目
├── environment.yml                 # Conda 环境
├── requirements.txt                # pip 依赖
├── requirements-dev.txt
├── README.md  ROADMAP.md  NEXT_STEPS.md  CLAUDE.md
```

### 三区流向图

```
inputs/                              workspace/                   outputs/
───────                              ──────────                   ────────
data/cache ──────────────┐
data/derived ────────────┤
pools/(X) ───────────────┤
configs/profiles/(Z) ────┼──→ X×Y×Z 全量训练 ──→ IC报告 ──→ reports/
configs/experiments/ ────┤         │
src/models/(Y) ──────────┘         ├──→ 筛选 ──→ registry/certified.json
                                   │                 │
                                   └──→ 迭代重训 ←──┘  (每周)
                                         │
                                         └──→ 推理 ──→ predictions/
                                                           │
                                                   交易策略层消费
```

### 与当前目录的映射

| 当前路径 | 目标路径 | 动作 |
|---------|---------|------|
| `data/cache/` | `inputs/data/cache/` | 移动 |
| `data/datasets/_smoke_*` | 清理 | 删除（审计后） |
| `configs/stock_pools/` | `inputs/pools/` | 重组（config + symbols 跟策略代码放一起） |
| `configs/pipeline.yaml` | `inputs/configs/pipeline.toml` | 移动 + 重命名 |
| `configs/data_source.yaml` | `inputs/configs/data_source.toml` | 移动 + 重命名 |
| `configs/model_mtl.yaml` | `inputs/configs/profiles/` | 移动 |
| `configs/datasets/` | `inputs/configs/profiles/` | 合并 |
| `configs/experiments/` | `inputs/configs/experiments/` | 移动 |
| `models/*.pt` | `workspace/checkpoints/` | 移动 |
| `output/recommendations/` | `outputs/predictions/` | 重命名 |
| `output/reports/` | `outputs/reports/` | 移动 |
| `output/datasets/` | `workspace/` 或清理 | 审计后决定 |
| `logs/` | `workspace/runs/` | 合并 |
| `experiments/` | `docs/research/`（唯一文件） | 归并后删除目录 |
| `docs/archive/` `docs/branch_tasks/` | `docs/` | 扁平化 |
| `scripts/__pycache__/` | `.gitignore` | 移除跟踪 |
| `.claude/skills/` | 已从 git 移除 | 不变 |
| `.agents/skills/` | 已从 git 移除 | 不变 |

### Q: 清理激进程度 ✅ 已确认

**Programmer 决策**: **最激进** — 架构搬迁完成后直接删除老内容，不归档不保留。

- `data/datasets/_smoke_*`（34 个）：直接删除
- `output/recommendations/`（~40 个历史 JSON）：直接删除
- `output/reports/` 中旧 IC 报告：直接删除
- `models/best_mtl.pt` / `latest_mtl.pt` / `rolling_dim19/`：直接删除（基于 AkShare，TuShare 后重建）
- `docs/archive/` `docs/branch_tasks/`：文档类保留，扁平化归入 `docs/`
- 注意：`daily_pipeline.py` 对 `models/latest_mtl.pt` 的硬编码引用需在路径修复 Worktrack 中处理

## Scope Boundary

### In Scope

- 一级目录重组：`data/` → `inputs/data/`、`models/` → `workspace/checkpoints/`、`output/` → `outputs/`、`logs/` → `workspace/runs/`、`experiments/` → 解散
- `configs/` 内容迁移到 `inputs/configs/` 并重组子目录（profiles/ experiments/）
- `configs/stock_pools/` 移动到 `inputs/pools/`
- `.gitignore` 更新（覆盖新位置、排除 `__pycache__/`）
- `docs/` 子目录扁平化（archive/ branch_tasks/ 清理）
- 所有硬编码路径的修复（scripts/ configs/ src/ deployment/）
- 全量 pytest 回归
- 文档入口更新（README.md 等目录引用）

### Out of Scope

- `src/ashare_lab/` 内部模块重组
- `src/ashare_lab/` 的 import 路径变更
- TuShare 数据湖构建（后续 Milestone）
- 模型重训练或超参调整
- Pipeline 业务逻辑变更
- SQLite/数据库引入
- `data/cache/` 内容清理（~990 AkShare CSV 保留）
- `scripts/` 按用途分组（推迟到后续）

## Non Goals

- 不改变任何 Python import 路径
- 不改变训练/回测/推荐流水线的业务行为
- 不引入新依赖
- 不做 TuShare 数据迁移

## Acceptance Signals

1. 一级目录从 21 个减少到 ≤12 个
2. `inputs/` `workspace/` `outputs/` 三区存在且语义正确：
   - `inputs/` 只存数据、选股池、配置
   - `workspace/` 只存 checkpoints、运行日志、registry
   - `outputs/` 只存预测、报告、信号
3. `models/` `logs/` `experiments/` 不再作为一级目录
4. `__pycache__/` 不在 git 跟踪中
5. 全量 pytest 397/397 pass
6. `scripts/daily_pipeline.py --dry-run` 可正常执行
7. 根目录 README.md 目录说明与实际一致

## Suggested Milestone Brief

```yaml
milestone_id: MS-R2-001
title: Repo 目录排布重构 — inputs/workspace/outputs 三区模型
milestone_kind: goal-driven
priority: 3
depends_on: MS-R1-001  # 模型层已统一，src/ 内部结构稳定
purpose: >
  将 Repo 从探索期 21 个一级目录的散乱布局收敛为以 src/ 代码为核心、
  inputs/ → workspace/ → outputs/ 三区清晰分层的 ≤12 个一级目录，
  明确服务于 X×Y×Z 组合测试矩阵 + 滚动重训验证的核心工作流。
candidate_worktracks:
  - WT-R2-A1: 全量路径引用审计 → 生成 change-impact map（所有硬编码路径 + 交叉引用）
  - WT-R2-A2: inputs/ 区落成 — data/ configs/ pools/ 迁移 + config 重组
  - WT-R2-A3: workspace/ 区落成 — checkpoints/ runs/ registry/ 建立
  - WT-R2-A4: outputs/ 区落成 — predictions/ reports/ signals/ 建立
  - WT-R2-A5: 历史残留清理 — experiments/ docs/archive/ docs/branch_tasks/ _smoke_*
  - WT-R2-A6: 路径引用全量修复 — scripts/ configs/ src/ deployment/
  - WT-R2-A7: .gitignore 更新 + __pycache__ 清理 + docs 交叉引用修复
  - WT-R2-A8: 全量回归验证 — pytest + daily_pipeline dry-run + README 更新
completion_signals:
  - inputs/ workspace/ outputs/ 三区各就各位
  - 一级目录 ≤12
  - models/ logs/ experiments/ 不再作为一级目录
  - __pycache__ 不在 git 跟踪
  - 全量 397 tests pass
  - daily_pipeline --dry-run 正常
acceptance_criteria:
  - pytest 全量通过（≥397）
  - git status 干净
  - 目录移动后无 broken import 或路径错误
  - 根目录 README.md 与实际一致
```

## Confirmation State

- confirmation_required: false
- programmer_confirmed: true
- answered_questions:
  - Q1 一级目录模型: 3 区模型（inputs/workspace/outputs + 独立 src/）
  - Q1b experiments/ 位置: inputs/configs/experiments/
  - Q1c Milestone 范围: 只做目录重组，不含 TuShare 迁移
  - Q2 清理激进程度: 最激进 — 老产物直接删除
- unresolved_questions: []

## Continuation State

- continuation_required: false
- continuation_reason: N/A — all blocking questions resolved
- answered_questions: [Q1, Q1b, Q1c, Q2]
- unresolved_questions: []

## Handoff To Init Milestone

- ready_for_handoff: true
- blocks_init_milestone: none
- milestone_review_gate_handoff:
  - review_status: effective_pass
  - milestone_review_count: 1
  - latest_review_checkpoint: MS-R2-001-intake-2026-06-23T01:00:00+08:00
  - effective_review_pass: true

## Skip Record

- intake_skipped: false
