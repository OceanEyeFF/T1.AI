# 股票池 TOML Schema

> MS-R2-001 | 2026-06-23

## 必填字段

每个 `inputs/pools/<strategy>/config.toml` 必须包含：

```toml
stock_pool_id = "custom_low_manipulation"   # 唯一标识
stock_pool_version = "v1"                   # 版本号
pool_family = "custom"                      # custom | csi300 | sector_single | sector_corr | sector_anti_corr
pool_label = "低控盘概率池 (score >= 60)"    # 人类可读标签
construction_method = "..."                 # 构建方法描述
base_universe = "..."                       # 基础股票全集描述
symbols_source = "inputs/pools/low_manipulation/symbols.csv"  # 符号来源
symbols_csv = "inputs/pools/low_manipulation/symbols.csv"     # CSV 路径（相对 registry root）
symbols_count = 14                          # 股票数量
rebalance_frequency = "frozen"              # frozen | monthly | weekly
effective_start = "2023-01-01"             # 生效起始日
effective_end = ""                          # 空 = 无期限
is_default = false                          # 是否默认池
is_research_only = false                    # 是否仅研究用途
owner = "WT-EXPAND-001"                    # 负责人/Worktrack
notes = "..."                               # 备注
```

## symbols.csv 格式

```csv
symbol
000001
600519
...
```

必须包含列名 `symbol`、`code` 或 `ts_code` 之一。

## Registry 自动发现

`load_stock_pool_registry("inputs/pools")` 通过 `rglob("*.toml")` 自动发现所有子文件夹中的 TOML 文件。

## 与代码的映射

```
inputs/pools/low_manipulation/
├── config.toml          # 池定义（Registry 读取）
├── symbols.csv          # 股票列表
└── metadata.json        # 导出元数据

src/ashare_lab/stock_pool/low_manipulation/
├── strategy.py          # 选股策略代码（StockPoolStrategy ABC）
└── config.toml          # 策略参数（与 inputs/ 下的 TOML 不同）
```
