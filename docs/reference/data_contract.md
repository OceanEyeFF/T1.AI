# 数据契约规范

> MS-R2-001 | 2026-06-23

## 缓存数据 Schema

`inputs/data/cache/` 中的日K数据（parquet 格式）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | datetime64[ns] | 交易日（索引，升序） |
| `open` | float64 | 开盘价（前复权） |
| `high` | float64 | 最高价 |
| `low` | float64 | 最低价 |
| `close` | float64 | 收盘价 |
| `volume` | float64 | 成交量 |
| `amount` | float64 | 成交额 |

**分区规则**：`{data_source}/{symbol}/year={YYYY}/part.parquet`

**复权口径**：统一使用前复权（qfq），由 `tushare_source.py` 保证。

## 数据集 Schema

`dataset/builder.py` 产出的序列数据集（parquet 格式）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `features` | float32[N, seq_len, n_features] | 特征张量 |
| `label_3d` | float32[N] | 3 日 forward return |
| `label_5d` | float32[N] | 5 日 forward return |
| `label_10d` | float32[N] | 10 日 forward return |
| `symbol` | str[N] | 股票代码 |
| `date` | datetime64[ns][N] | 交易日 |

## 预测输出 Schema

`outputs/predictions/{date}.json`：

```json
{
  "date": "2026-06-23",
  "generated_at": "2026-06-23T15:30:00+08:00",
  "model": "transformer",
  "checkpoint": "workspace/checkpoints/transformer_latest.pt",
  "horizons": {
    "3d": [{"rank": 1, "symbol": "600519", "name": "贵州茅台", "predicted_return": 0.023}],
    "5d": [...],
    "10d": [...]
  }
}
```
