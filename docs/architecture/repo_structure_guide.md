# Repo 目录结构与维护指南

> 维护者：OceanEyeFF | 更新：2026-06-23 | MS-R2-001

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
├── src/ashare_lab/                 # Y 轴：模型代码（独立一级）
│   ├── data/                       # 数据适配器（AkShare/TuShare/ODP）
│   ├── stock_pool/                 # 选股策略（StockPoolStrategy ABC）
│   ├── dataset/                    # 数据集构建（序列/市场状态 builder）
│   ├── features/                   # 技术特征（Return/RSI/MACD/Bollinger...）
│   ├── labels/                     # 标签生成（3d/5d/10d forward return）
│   ├── models/                     # 模型架构（Transformer/LSTM/XGBoost + ModelABC）
│   ├── training/                   # 训练器（early stopping/checkpoint）
│   ├── evaluation/                 # 评估指标（IC/RankIC/月胜率）
│   ├── pipeline/                   # 日频流水线编排器（5阶段）
│   ├── recommendation/             # 推荐引擎 + 持久化 + 验证
│   ├── backtest/                   # 回测引擎（T+1/涨跌停约束）
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
├── .servo/                         # Harness 控制面（milestone/worktrack/control artifacts）
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
| `data/datasets/` | 已删除 | 旧 AkShare 数据集，后续 TuShare 重建 |
