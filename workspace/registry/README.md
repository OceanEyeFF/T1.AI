# registry/ — 配对认证注册表

记录 X×Y×Z 训练后通过 IC 滚动验证的模型配对。

## certified.json 格式

```json
{
  "pairs": {
    "low_manipulation_xgb_10feat_3d5d10d": {
      "pool": "custom_low_manipulation",
      "model": "xgboost",
      "config_profile": "10feat_3d5d10d",
      "checkpoint": "workspace/checkpoints/low_manipulation_xgb.pt",
      "ic_series": {"3d": {"mean": 0.045, "std": 0.02}},
      "certified_at": "2026-06-23",
      "last_retrain": "2026-06-23"
    }
  },
  "updated": "2026-06-23T00:00:00+08:00"
}
```

## 认证流程

1. X×Y×Z 全量扫荡 → 筛选出 IC 最高的组合
2. 对筛选出的组合执行滚动重训 → 采集 IC 时间序列
3. IC 稳定性达标 → 写入 certified.json
4. 交易策略层（Layer 2）只消费 certified.json 中的配对

当前状态：空文件。认证逻辑待训练实验框架就绪后实现。
