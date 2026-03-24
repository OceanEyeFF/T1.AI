# 配置与实验产物命名/版本规范（2026-03-11）

## 1. 背景与目的

本文档用于统一项目中配置文件、实验产物和核心 ID 体系的命名与版本规则。

### 1.1 当前问题

- `configs/` 下 YAML 和 TOML 混合，无统一命名规则
- 仅 `lstm_rolling_baseline.toml` 有 `model_track`/`config_profile`/`config_status` 字段，其余配置文件缺失
- 实验产物（`output/reports/`）全部平铺，无结构化 metadata
- `data/datasets/` 中正式数据集与临时/smoke 目录混杂
- `dataset_id`、`experiment_id` 等核心 ID 尚无正式定义
- 配置文件在分支间的兼容性无规则可依

> 说明：以上是 2026-03-11 的治理快照。到 2026-03-24，`develop` 已补齐主线实验 metadata / `_effective_config.json` / `output/reports/{model_track}` 最小闭环，且 4 个 mainline 实验 TOML 已补齐统一元数据字段。

### 1.2 与已有基线的关系

本文档建立在以下已有基线之上，必须对齐而非覆盖：

- [股票池 Registry 基线](../modules/stock_pool_registry_baseline_20260311.md)：已定义 `stock_pool_id`、`stock_pool_version`
- [双窗口评估基线](dual_window_evaluation_baseline_20260311.md)：已定义 `evaluation_window_id`
- [文档命名与落盘规则](doc_governance.md)：已定义文档命名约定
- [文档生命周期规则](doc_lifecycle_rules_20260311.md)：已定义文档状态语义

---

## 2. configs/ 命名规范

### 2.1 目录结构

```
configs/
├── datasets/              # 数据集构建配置
│   └── 1d_independent/    # 模型线子目录（按需）
├── experiments/            # 实验/训练运行配置
│   └── 1d_independent/    # 模型线子目录（按需）
├── stock_pools/            # 股票池 registry 配置
├── evaluations/            # 评估窗口/门禁配置（待建）
├── data_source.yaml        # 数据源配置（全局，保留 YAML）
├── pipeline.yaml           # 流水线配置（全局，保留 YAML）
└── protocol.yaml           # 交易协议配置（全局，保留 YAML）
```

**规则：**

1. **新增配置一律使用 TOML 格式**
2. 已有的顶层 YAML（`data_source.yaml`、`pipeline.yaml`、`protocol.yaml`）保留不动，属于全局基础设施配置
3. `model_mtl.yaml` 作为旧版模型配置保留，后续由 TOML 实验配置逐步替代
4. 按功能分类到子目录：`datasets/`、`experiments/`、`stock_pools/`、`evaluations/`
5. 模型线可在子目录内再建子目录（如 `1d_independent/`），但**不超过两层**

`configs/stock_pools/` 已在 2026-03-24 落地，用于股票池 registry 配置。

### 2.2 文件命名规则

TOML 配置文件命名统一为：

```
{backbone}_{task_scope}_{profile_tag}.toml
```

各段含义：

| 段 | 含义 | 示例值 |
|----|------|--------|
| `backbone` | 模型骨架 | `lstm`、`xgb`、`transformer` |
| `task_scope` | 任务/运行范围 | `rolling`、`direction`、`panel` |
| `profile_tag` | 配置定位标签 | `baseline`、`candidate_v2`、`fastpilot`、`ablation_no_hist_hl` |

**示例：**

- `lstm_rolling_baseline.toml` — LSTM 滚动训练基线
- `xgb_rolling_baseline.toml` — XGBoost 滚动训练基线
- `xgb_direction_baseline.toml` — XGBoost 方向预测基线（1d 独立）
- `xgb_direction_no_hist_hl.toml` — XGBoost 去除历史高低价消融

**数据集配置文件命名：**

```
{dataset_type}_{pool_or_scope}_{profile_tag}.toml
```

| 段 | 含义 | 示例值 |
|----|------|--------|
| `dataset_type` | 数据集类型 | `sequence`、`market_state`、`panel` |
| `pool_or_scope` | 股票池或范围 | `quick8`、`sector70`、`csi300` |
| `profile_tag` | 配置定位标签 | `baseline`、`candidate`、`stability52` |

**示例：**

- `sequence_dataset_baseline.toml`（兼容现有）
- `market_state_dataset_baseline.toml`（兼容现有）
- `market_state_sector70_stability52.toml`（推荐新格式）

### 2.3 配置文件必须包含的元数据字段

所有 **experiments/** 下的 TOML 文件，必须在末尾声明：

```toml
# --- 元数据（必须） ---
seed = 42
model_track = "mainline_3510d"         # 见 § 4.1
config_profile = "lstm_rolling_baseline"  # 见 § 4.2
config_status = "baseline"             # 见 § 5
```

所有 **datasets/** 下的 TOML 文件，必须在末尾声明：

```toml
# --- 元数据（必须） ---
# dataset_id 由构建脚本自动生成，此处声明生成规则的关键参数
# 格式见 § 4.3
```

---

## 3. 实验产物目录结构

### 3.1 输出根目录

```
output/
├── reports/                # 实验报告（IC 报告、门禁报告等）
│   ├── mainline_3510d/     # 按 model_track 分目录
│   └── 1d_independent/     # 按 model_track 分目录
├── datasets/               # 构建完成的数据集索引/轻量元数据
└── recommendations/        # 推荐结果（已有，按日期命名）
```

`data/datasets/` 仍保留作为大体积数据集的物理存储位置（已 gitignored），但
`output/datasets/` 可放置轻量元数据索引。

### 3.2 reports/ 子目录规则

**按 model_track 分目录：**

```
output/reports/{model_track}/
```

**报告文件命名：**

```
{backbone}_{profile_tag}_{date_YYYYMMDD}.{ext}
```

**示例：**

```
output/reports/mainline_3510d/lstm_baseline_20260309.json
output/reports/mainline_3510d/xgb_baseline_20260309.json
output/reports/mainline_3510d/lstm_baseline_20260309_oos.parquet
output/reports/1d_independent/xgb_direction_baseline_20260309.json
output/reports/1d_independent/xgb_direction_no_hist_hl_sector70_20260309.json
```

### 3.3 必须包含的 metadata 文件

每次实验运行，除主报告外，必须输出一个 `_effective_config.json`：

```json
{
  "experiment_id": "lstm_rolling_baseline_mainline_3510d_20260324",
  "model_track": "mainline_3510d",
  "config_profile": "lstm_rolling_baseline",
  "config_status": "baseline",
  "stock_pool_id": "custom_quick8",
  "stock_pool_version": "v1",
  "evaluation_window_id": "fixed_20230101_20250701",
  "dataset_id": "seq_quick8_53d_20230101_20260305",
  "seed": 42,
  "generated_at": "2026-03-24T14:30:00+08:00",
  "script": "run_lstm_rolling_retrain_dim19_regime",
  "config_file": "configs/experiments/lstm_rolling_baseline.toml"
}
```

**必填字段清单（最小集）：**

| 字段 | 来源 | 说明 |
|------|------|------|
| `experiment_id` | 运行时拼接 | 见 § 4.6 |
| `model_track` | 配置文件 | 见 § 4.1 |
| `config_profile` | 配置文件 | 见 § 4.2 |
| `config_status` | 配置文件 | 见 § 5 |
| `stock_pool_id` | 配置文件或默认 | 见 § 4.4 |
| `evaluation_window_id` | 运行参数 | 见 § 4.5 |
| `dataset_id` | 数据集元数据 | 见 § 4.3 |
| `seed` | 配置文件 | 随机种子 |
| `generated_at` | 运行时 | ISO 8601 时间戳 |
| `script` | 运行时 | 入口脚本名 |
| `config_file` | 运行时 | 使用的配置文件路径 |

### 3.4 data/datasets/ 临时目录规则

| 前缀 | 含义 | 生命周期 |
|------|------|----------|
| `_smoke_*` | 冒烟测试数据 | 用完可删 |
| `_tmp_*` | 临时调试数据 | 用完可删 |
| 无特殊前缀 | 正式数据集 | 需登记到 metadata |

定期清理规则：`_smoke_*` 和 `_tmp_*` 目录超过 14 天未修改即可删除。

---

## 4. 完整 ID 体系定义

### 4.1 `model_track` — 模型线标识

标识一条独立的模型研究线，决定了任务定义、标签体系和评估口径。

**当前冻结值：**

| model_track | 含义 | 对应分支 |
|-------------|------|----------|
| `mainline_3510d` | 主模型线（3d/5d/10d 多任务） | develop / feature/model-3d-5d-10d-head |
| `1d_independent` | 1d 独立研究线 | feature/model-d1-research |

**命名规则：**
- 小写字母 + 数字 + 下划线
- 不含空格、连字符或中文
- 新增 model_track 须在本文档追加登记

### 4.2 `config_profile` — 配置档标识

标识同一模型线下的一组特定配置参数组合。

**命名规则：**

```
{backbone}_{task_scope}_{profile_tag}
```

与配置文件名一致（去掉 `.toml` 后缀即为 config_profile）。

**示例：**

| config_profile | 说明 |
|----------------|------|
| `lstm_rolling_baseline` | LSTM 滚动训练基线 |
| `xgb_rolling_baseline` | XGBoost 滚动训练基线 |
| `xgb_direction_baseline` | XGBoost 方向预测基线（1d） |
| `lstm_rolling_fastpilot` | LSTM 快速验证（缩减 epoch） |

### 4.3 `dataset_id` — 数据集标识

标识一份已构建的数据集（含特征、标签、split）。

**命名规则：**

```
{type_abbr}_{pool_scope}_{feature_dim}d_{date_range}
```

| 段 | 含义 | 示例 |
|----|------|------|
| `type_abbr` | 数据集类型缩写 | `seq`（sequence）、`mkt`（market_state）、`panel` |
| `pool_scope` | 股票池/范围 | `quick8`、`sector70`、`csi300` |
| `feature_dim` | 特征维度数 | `19`、`44`、`52`、`58` |
| `date_range` | 起止日期 | `20230101_20260120` |

**示例：**

| dataset_id | 对应物理目录 |
|------------|------------|
| `seq_quick8_52d_20230101_20260120` | `lstm_quick8_52d_no_hist_hl_20230101_20260120_ts` |
| `mkt_sector70_44d_20210101_20260120` | `lstm_sector70_19d_mkt_20210101_20260120` |

**说明：**
- dataset_id 是逻辑 ID，物理目录名允许更详细但必须可映射
- 构建脚本在输出 metadata 时必须同时记录 `dataset_id` 和物理 `output_dir`
- 同一 dataset_id 如果构建参数不同（如特征筛选变化），必须升版本（见 § 6）
- 截至 2026-03-24，`sequence` 与 `market_state` 两条构建链路都已开始自动写入 `dataset_id`，并同步记录 `stock_pool_id` / `stock_pool_version` / `stock_pool_registry_path`

### 4.4 `stock_pool_id` — 股票池标识

**直接引用已有基线定义：** [stock_pool_registry_baseline_20260311.md § 4.1](../modules/stock_pool_registry_baseline_20260311.md)

当前冻结的 ID 家族：

| stock_pool_id 家族 | 含义 |
|-------------------|------|
| `csi300` | 沪深300冻结基线池 |
| `sector_single_*` | 单板块/单行业池 |
| `sector_corr_*` | 高相关板块联动池 |
| `sector_anti_corr_*` | 反板块/对冲视角池 |
| `custom_*` | 实验型自定义池 |

**对齐要求：**
- 本规范中 `stock_pool_id` 的取值必须来自 registry 基线定义
- 配置文件中使用 `stock_pool_id` 时，不得自行发明新的 ID 家族
- 不写 `stock_pool_id` 的旧配置，默认隐含 `stock_pool_id = "csi300"` 或由 `symbols_csv` 推断
- 到 2026-03-24，`develop` 的主线实验配置已显式补齐 `stock_pool_id` / `stock_pool_version` / `evaluation_window_id` / `dataset_id`，不再依赖文档手工补注

### 4.5 `evaluation_window_id` — 评估窗口标识

**直接引用已有基线定义：** [dual_window_evaluation_baseline_20260311.md](dual_window_evaluation_baseline_20260311.md)

当前冻结值：

| evaluation_window_id | 含义 |
|---------------------|------|
| `fixed_20230101_20250701` | 固定基准窗口 |
| `latest_rolling` | 最近 12 个月滚动窗口 |

**对齐要求：**
- 与 stock_pool_id 同理，不得自行发明新的 evaluation_window_id
- 变更窗口定义必须通过 baseline 升级流程（见评估基线文档 § 8）

### 4.6 `experiment_id` — 实验标识

标识一次具体实验运行，是所有其他 ID 的组合定位。

**拼接规则：**

```
{config_profile}_{model_track}_{date_YYYYMMDD}
```

**示例：**

| experiment_id | 说明 |
|---------------|------|
| `lstm_rolling_baseline_mainline_3510d_20260309` | LSTM 基线在主线上的 2026-03-09 运行 |
| `xgb_direction_baseline_1d_independent_20260309` | XGB 方向预测基线在 1d 线的运行 |

**说明：**
- 实验 ID 不写入配置文件，由运行脚本在执行时自动拼接
- 实验 ID 的唯一性由 `config_profile` + `model_track` + 日期保证
- 同日多次运行可追加序号后缀：`_run2`、`_run3`

---

## 5. 配置状态三分类

### 5.1 状态定义

| 状态 | 含义 | 配置文件中的值 |
|------|------|--------------|
| `baseline` | 当前默认基线，稳定可引用，实验横比的锚点 | `config_status = "baseline"` |
| `candidate` | 候选配置，正在验证中，未通过门禁前不得替代 baseline | `config_status = "candidate"` |
| `frozen` | 冻结快照，不再修改，仅用于历史回溯 | `config_status = "frozen"` |

### 5.2 流转规则

```
candidate ──(通过门禁)──→ baseline ──(被新 baseline 替代)──→ frozen
                              │
                              └──(如从未被替代，持续为 baseline)
```

**规则：**

1. **新配置必须从 `candidate` 状态开始**
   - 不允许直接创建 `baseline` 配置（除非是首个基线，无前驱可比）
2. **candidate → baseline 的条件**
   - 在双窗口评估下，至少一项核心指标（IC / ICIR / 回测 Sharpe）优于或等于当前 baseline
   - 通过 `compare_ic_reports.py --gate-icir` 等门禁脚本验证
   - 门禁结果记录到 `_effective_config.json` 或独立门禁报告
3. **baseline → frozen 的条件**
   - 当新的 candidate 正式升级为 baseline 后，旧 baseline 自动变为 frozen
   - frozen 配置不再接受修改，如需基于其调整须复制为新 candidate
4. **frozen 配置的处置**
   - 保留配置文件不删除
   - 可移入 `configs/archive/` 目录（可选）
   - 必须保持可读、可复现

### 5.3 使用示例

```
时间线：
T0: configs/experiments/xgb_rolling_baseline.toml  (config_status = "baseline")
T1: 新增 xgb_rolling_candidate_v2.toml             (config_status = "candidate")
T2: candidate_v2 通过门禁
    → xgb_rolling_candidate_v2.toml 改为 config_status = "baseline"
    → 原 xgb_rolling_baseline.toml 改为 config_status = "frozen"
    → 可选：将原文件移入 configs/archive/experiments/
```

### 5.4 特殊状态：fastpilot

`fastpilot` 不是配置状态，而是一种 profile_tag，表示快速验证配置（通常缩减训练轮次）：

- fastpilot 配置的 `config_status` 固定为 `candidate`
- fastpilot 不能直接升级为 baseline（必须用完整参数重新跑）
- fastpilot 的作用是快速排除明显不可行的方案

---

## 6. 版本升级规则

### 6.1 必须升版本的变化

以下任一变化，都必须生成新版本（不得原地修改）：

| 范围 | 变化类型 | 动作 |
|------|---------|------|
| 配置文件 | 模型超参变化（lr、hidden_size、层数等） | 新建 candidate 配置 |
| 配置文件 | 数据集引用变化（dataset_dir、symbols_csv） | 新建 candidate 配置 |
| 配置文件 | 窗口参数变化（train/valid/test weeks） | 新建 candidate 配置 |
| 配置文件 | 损失函数/权重变化 | 新建 candidate 配置 |
| 数据集 | 特征列增减 | 新 dataset_id |
| 数据集 | 标签定义变化（horizons、label_mode） | 新 dataset_id |
| 数据集 | 股票池成分变化 | 新 stock_pool_version |
| 数据集 | 时间范围变化 | 新 dataset_id |
| 股票池 | 筛选条件/成分变化 | 新 stock_pool_version |
| 评估窗口 | 边界/长度/逻辑变化 | 新 evaluation_window_id |

### 6.2 不需要升版本的变化

| 变化类型 | 动作 |
|---------|------|
| 注释/文档修正 | 原地编辑即可 |
| 格式化/空白调整 | 原地编辑即可 |
| `seed` 变化（用于多种子验证） | 在 experiment_id 中追加种子信息 |
| 输出路径调整（不影响实验结果） | 原地编辑即可 |

### 6.3 版本号格式

| ID 类型 | 版本格式 | 示例 |
|---------|---------|------|
| `stock_pool_version` | `v{N}` 或 `{YYYYMMDD}_v{N}` | `v1`、`20260311_v1` |
| `evaluation_window_id` | 内嵌版本（ID 本身即版本） | `fixed_20230101_20250701` |
| `config_profile` | 在 profile_tag 中体现 | `lstm_rolling_baseline`→`lstm_rolling_candidate_v2` |
| `dataset_id` | 通过日期范围区分 | `seq_quick8_52d_20230101_20260120` |

---

## 7. 当前配置盘点与合规评估

### 7.1 develop 分支配置

| 文件 | model_track | config_profile | config_status | 合规 | 待修正 |
|------|-------------|----------------|---------------|------|--------|
| `experiments/lstm_rolling_baseline.toml` | `mainline_3510d` | `lstm_rolling_baseline` | `baseline` | ✅ | — |
| `experiments/lstm_rolling_fastpilot.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐三字段 |
| `experiments/xgb_rolling_baseline.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐三字段 |
| `experiments/xgb_rolling_fastpilot.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐三字段 |
| `datasets/sequence_dataset_baseline.toml` | — | — | — | ⚠️ | 建议补注释 |
| `datasets/market_state_dataset_baseline.toml` | — | — | — | ⚠️ | 建议补注释 |

### 7.2 feature/model-d1-research 分支配置

| 文件 | model_track | config_profile | config_status | 合规 | 待修正 |
|------|-------------|----------------|---------------|------|--------|
| `experiments/1d_independent/xgb_direction_baseline.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐 |
| `experiments/1d_independent/xgb_direction_no_hist_hl.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐 |
| `experiments/1d_independent/xgb_direction_no_hist_hl_stability52.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐 |
| `experiments/1d_independent/xgb_direction_no_hist_hl_sector70_stability52.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐 |
| `experiments/xgb_rolling_d1_close_candidate.toml` | ❌ 缺失 | ❌ 缺失 | ❌ 缺失 | ❌ | 补齐 |

### 7.3 顶层 YAML 合规评估

| 文件 | 状态 | 说明 |
|------|------|------|
| `data_source.yaml` | ✅ 保留 | 全局基础设施，无需 model_track |
| `pipeline.yaml` | ✅ 保留 | 全局流水线配置 |
| `protocol.yaml` | ✅ 保留 | 交易协议，与模型线无关 |
| `model_mtl.yaml` | ⚠️ 旧版 | 被 TOML 实验配置逐步替代，保留但标注 `legacy` |

### 7.4 output/reports/ 合规评估

当前全部平铺在 `output/reports/` 下：

| 文件 | 待调整 |
|------|--------|
| `xgb_nextopen_baseline_quick8_20260309.json` | 应移入 `output/reports/mainline_3510d/` |
| `xgb_d1_close_candidate_quick8_20260309.json` | 应移入 `output/reports/mainline_3510d/` 或 `1d_independent/` |
| `ic_monthly_*` | 应移入对应 model_track 子目录 |
| `model_candidate_gate_summary_*` | 应移入对应 model_track 子目录 |
| `*_effective_config.json` | ✅ 已有该模式 |

---

## 8. 与已有基线的对齐确认

### 8.1 stock_pool_registry_baseline 对齐

| 项目 | 本规范 | Registry 基线 | 一致性 |
|------|--------|-------------|--------|
| stock_pool_id 命名 | 引用 registry | 已定义 | ✅ 一致 |
| stock_pool_version 格式 | `v{N}` / `{YYYYMMDD}_v{N}` | 同 | ✅ 一致 |
| pool_family | 不定义（属 registry） | 已定义 | ✅ 分工明确 |
| 配置文件中引用方式 | `stock_pool_id = "csi300"` | 同 | ✅ 一致 |

### 8.2 dual_window_evaluation_baseline 对齐

| 项目 | 本规范 | 评估基线 | 一致性 |
|------|--------|---------|--------|
| evaluation_window_id 值域 | `fixed_*` / `latest_rolling` | 同 | ✅ 一致 |
| 报告必记字段 | experiment_id + 窗口 ID | 同（§ 5.2） | ✅ 一致 |
| 变更规则 | 须新增 ID，不覆盖 | 同（§ 8） | ✅ 一致 |

### 8.3 实验报告联合字段

综合本规范与已有基线，一份完整的实验报告 metadata 至少包含：

```json
{
  "experiment_id": "...",
  "model_track": "...",
  "config_profile": "...",
  "config_status": "...",
  "stock_pool_id": "...",
  "stock_pool_version": "...",
  "evaluation_window_id": "...",
  "window_start": "...",
  "window_end": "...",
  "dataset_id": "...",
  "seed": 42,
  "generated_at": "..."
}
```

这与 [评估基线 § 5.2](dual_window_evaluation_baseline_20260311.md) 要求的字段集是**超集**关系。

---

## 9. 与公用层抽象的关系

G3 已完成，参见 [shared_layer_inventory_20260311.md](shared_layer_inventory_20260311.md)。

### 9.1 G3 盘点对本规范的支撑

| G3 结论 | 对 G4 的影响 |
|---------|-------------|
| `scripts/config_io.py` 两条线完全一致 | ✅ config parser 已是公用层，后续补齐元数据字段时无需分支适配 |
| 输入 contract 完全一致 | ✅ dataset 构建脚本可以共享 dataset_id 生成逻辑 |
| 评估基础工具（metrics.py）一致 | ✅ effective_config 中评估相关字段读取可统一 |
| `compare_ic_reports.py` 1d 版本更通用 | ⚠️ 若采纳 1d 的 horizon-generic 版本，门禁脚本输出的 metadata 格式可能需微调 |

### 9.2 联动落地建议

1. **config parser 公用层确认：** `scripts/config_io.py` 无需抽象改造，直接作为公用层使用
2. **effective_config 生成统一：** 建议在公用层中增加 `generate_effective_config()` 函数，统一输出本规范 § 3.3 定义的字段
3. **报告目录管理：** 按 `model_track` 分目录的逻辑可纳入公用层，两条线共享
4. **dataset metadata：** dataset_id 拼接规则（§ 4.3）可在数据集构建的公用层中实现

---

## 10. 第一阶段不做什么

- 不做自动化的配置迁移脚本（手工补齐即可）
- 不把所有已有配置文件重命名（只要求新增配置遵守规范）
- 不强制已有 `output/reports/` 文件立即搬迁（渐进迁移）
- 不定义配置文件的 JSON Schema 验证（后续有需求再做）
- 不在配置文件中嵌入完整的 metadata 冗余（用 _effective_config.json 承载）

---

## 11. 下一步建议

1. **已完成**：对 develop 分支上缺失元数据字段的 4 个实验配置文件补齐 `model_track`/`config_profile`/`config_status`
2. **1d 分支同步**：在 1d 分支的实验配置文件中补齐元数据字段（须在该分支操作）
3. **报告目录渐进整理**：脚本已默认写入按 `model_track` 分的子目录，后续仅做增量迁移
4. **stock_pools/ 目录**：`configs/stock_pools/` 已在股票池模组 S1 阶段创建并启用
5. **evaluations/ 目录**：在双窗口协议代码化时创建
6. **effective_config 升级**：主线最小闭环已完成，后续仅在新增字段时扩展
