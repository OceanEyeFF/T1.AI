# Repo 目录结构与维护指南

> 维护者：OceanEyeFF | 更新：2026-07-17 | MS-R2-001 + ashare_infra Phase 1 / 1.5

## 设计理念：三区模型

Repo 按流程阶段分为三个互不重叠的区，每个区有清晰的读写语义：

| 区 | 回答的问题 | 谁写 | 谁读 |
|----|-----------|------|------|
| `inputs/` | "用什么训练？" | 数据脚本、研究员 | 训练器、实验 runner |
| `workspace/` | "训练过程中产生了什么？" | 训练器 | 研究员、评估脚本 |
| `outputs/` | "模型产出了什么可用的？" | 推理脚本 | **交易策略层** |

`src/` 作为代码层独立于三区之外。

## 完整目录结构

```
T1.AI/
│
├── inputs/                         # ═══ Zone 1: 输入区 ═══
│   ├── data/
│   │   ├── cache/                  # 数据湖缓存（TuShare 日K/资金流/基本面 parquet）
│   │   └── derived/                # 高阶衍生特征（动量/波动率等，后续构建）
│   ├── pools/                      # X 轴：选股策略 → 股票代码集合
│   │   ├── low_manipulation/       #   低控盘策略（strategy.py + config.toml + symbols.csv）
│   │   ├── momentum/               #   动量策略（待实现）
│   │   └── value/                  #   价值策略（待实现）
│   └── configs/                    # Z 轴：配置档案
│       ├── profiles/               #   输入维度 × 输出 horizon 组合
│       ├── experiments/            #   X×Y×Z 实验矩阵定义
│       ├── pipeline.toml           #   日频流水线配置
│       ├── data_source.toml        #   数据源配置
│       └── protocol.yaml           #   协议定义
│
├── src/ashare_infra/               # 基础设施包（湖 / sim / guard）— Phase 1+
│   ├── lake/                       #   DataLake 唯一取数入口 + smoke + meta(stock_basic)
│   ├── data/                       #   tushare / odp / index 适配器
│   ├── guard/                      #   DataScope / FetchGate / metrics / temporal
│   └── sim/                        #   日频 paper broker + replay + BacktestEngine
│
├── src/ashare_exec/                # 执行策略包（Phase 3 / WT-EXEC-001）
│   ├── decision.py                 #   SimpleDecisionAPI：scores / ranked（可扩展 extras）
│   ├── weight_mapper.py            #   唯一权重产生点
│   ├── adapt.py                    #   Decision + Mapper → Strategy
│   └── strategies/                 #   MomentumTopN（走同一缝）；刀2 已含 ML stub
│
├── src/ashare_lab/                 # 研究/业务包（可经 shim 兼容旧 import）
│   ├── data/                       # 兼容 shim → ashare_infra.data（勿新写直调 load_or_fetch_*）
│   ├── stock_pool/                 # 选股策略（StockPoolStrategy ABC）
│   ├── dataset/                    # 数据集构建（序列/市场状态 builder）
│   ├── features/                   # 技术特征（Return/RSI/MACD/Bollinger...）
│   ├── labels/                     # 标签生成（3d/5d/10d forward return）
│   ├── models/                     # 模型架构（Transformer/LSTM/XGBoost + ModelABC）
│   ├── training/                   # 训练器（early stopping/checkpoint）
│   ├── evaluation/                 # 评估指标（shim → guard.metrics 为主）
│   ├── pipeline/                   # 日频流水线编排器（5阶段）
│   ├── recommendation/             # 推荐引擎 + 持久化 + 验证
│   ├── backtest/                   # 兼容 shim → ashare_infra.sim / backtest
│   ├── trend_schema.py             # 趋势预测 schema
│   ├── universe.py                 # 股票池过滤规则
│   ├── reporting.py                # 报告生成
│   └── utils.py                    # 工具函数
│
├── workspace/                      # ═══ Zone 2: 工作区 ═══
│   ├── checkpoints/                # 模型权重（*.pt, .gitignore 排除）
│   ├── runs/                       # 运行日志（pipeline.log, cron.log）
│   └── registry/                   # 配对认证注册表（certified.json）
│
├── outputs/                        # ═══ Zone 3: 输出区（交易层消费面）═══
│   ├── predictions/                # 定期推理输出（每日推荐 JSON/CSV）
│   ├── reports/                    # IC 时间序列 + 评估报告
│   └── signals/                    # （后续）交易策略层输入
│
├── scripts/                        # 入口脚本（build_*/ train_*/ eval_*/ run_*/ daily_*）
├── tests/                          # 测试（pytest）
├── docs/                           # 文档（modules/ research/ overview/ interfaces/ archive/）
├── deployment/                     # 部署配置（systemd timer/service + crontab.example）
│
├── pyproject.toml                  # Python 项目元数据
├── environment.yml                 # Conda 环境
├── requirements*.txt               # pip 依赖
├── README.md  ROADMAP.md  NEXT_STEPS.md  CLAUDE.md
└── .gitignore
```

## 维护规则

### 添加新选股策略

1. 在 `inputs/pools/<strategy_name>/` 下创建子文件夹
2. 包含 `config.toml`（符合 StockPoolRecord schema）+ `symbols.csv`
3. 可选：在 `src/ashare_lab/stock_pool/<strategy_name>/` 下放策略代码
4. 注册到 `inputs/pools/` 目录（registry 通过 `.toml` 文件自动发现）

### 添加新模型

1. 在 `src/ashare_lab/models/<model_name>/` 下创建子文件夹
2. 包含 `__init__.py`（实现 ModelABC）+ `config.toml`
3. 模型自动注册到 `models/registry.py`
4. Checkpoint 保存到 `workspace/checkpoints/`

### 添加新实验配置

1. 在 `inputs/configs/experiments/` 下创建 `.toml` 文件
2. 定义 X（pool）× Y（model）× Z（profile）组合
3. 实验产物（IC 报告）输出到 `outputs/reports/`

### .gitignore 覆盖规则

- `inputs/data/cache/` — 缓存数据不跟踪
- `workspace/checkpoints/` — 模型权重不跟踪
- `workspace/runs/` — 运行日志不跟踪
- `outputs/predictions/` — 推理输出不跟踪
- `outputs/reports/` — 评估报告不跟踪
- `*.pt *.pth *.ckpt` — 全局排除

## 与旧结构的对照

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `data/cache/` | `inputs/data/cache/` | 数据湖缓存 |
| `configs/pipeline.yaml` | `inputs/configs/pipeline.toml` | 流水线配置 |
| `configs/stock_pools/` | `inputs/pools/` | 选股池 |
| `models/*.pt` | `workspace/checkpoints/` | 模型权重 |
| `logs/` | `workspace/runs/` | 运行日志 |
| `runs/` | `workspace/checkpoints/` | 训练产物 |
| `output/recommendations/` | `outputs/predictions/` | 每日推荐 |
| `output/reports/` | `outputs/reports/` | 评估报告 |
| `experiments/` | 已删除 | 设计文档归入 docs/research/ |
| `data/datasets/` | 已删除 | 旧数据集目录，后续 TuShare 重建 |

## `ashare_infra` vs `ashare_lab` vs `ashare_exec`

| 包 | 职责 | 调用约定 |
|----|------|----------|
| `ashare_infra` | 数据湖、sim/paper、guard（scope/gate/metrics） | **唯一取数入口**是 `ashare_infra.lake.DataLake`；生命周期/交易边界走 `ashare_infra.guard`；引擎只认 `sim.engine.Strategy` |
| `ashare_exec` | 执行策略：Decision → **WeightMapper** → `Strategy.target_weights` | 见 [ashare_exec_guide.md](../guides/ashare_exec_guide.md)；**≠** `stock_pool` 选股 |
| `ashare_lab` | 研究与业务（dataset / models / recommendation / pool…） | 可通过历史 shim 兼容旧 `ashare_lab.data` / `sim` import；**业务代码不要直调** `load_or_fetch_*`（见约定测）；旧 `strategy/`/`strategies/` 已删（WT-EXEC-001） |

### Meta：`stock_basic`（WT-INFRA-001.5）

- Canonical 本地路径：`{cache_dir}/meta/stock_basic.csv` 或 `.parquet`
- API：`DataLake.load_stock_basic` / `load_symbol_lifecycle_map` / `with_stock_basic_meta`
- **本阶段不拉网**；与 MS-R4 对齐时可改常量或补 live pull，但不在 1.5 必过范围内
- 夹具参考：`tests/fixtures/infra_a/meta/stock_basic.csv`

### 取数约定（WT-INFRA-002）

- **唯一取数入口**：`ashare_infra.lake.DataLake`（含 `load_daily_bars` / `load_scope_bars` / `load_index_daily` / meta）
- **IC / RankIC**：`ashare_infra.guard.metrics`（`ashare_lab.evaluation.metrics` 仅为 shim）
- **禁止**：新业务代码 `from … import load_or_fetch_*`（适配器实现与 `ashare_infra.data.*` 内部除外）
- 约定测：`tests/contract/infra/test_no_direct_load_or_fetch.py`（validator / DatasetBuilder / 主要 scripts）
- **TuShare 缓存布局**：canonical `{cache_dir}/tushare_qfq/{ts_code}/year=*/part.parquet`（R4 湖合同）；`DataLake` 是唯一取数入口

### Shim 保留策略

- Phase 1 已把 data/sim/backtest 迁到 `ashare_infra`，`ashare_lab` 侧保留兼容 shim
- Phase 2 已将核心消费方切到 DataLake/guard；**仍不删除** shim，外部/脚本旧 import 可继续工作直到后续显式去 shim WT
