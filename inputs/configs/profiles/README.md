# profiles/ — Z 轴配置档案

定义输入维度 × 回溯窗口 × 输出 horizon 组合。

每个 `.toml` 文件是一个独立的配置档案：

```toml
profile_id = "10feat_3d5d10d"
input_dims = 10
lookback_days = 20
output_horizons = [3, 5, 10]
label_type = "forward_return"
```

当前状态：`model_mtl.toml`（从旧 configs/ 迁移）。后续按实验需求新增。
