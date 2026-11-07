# profiles/ — Z 轴配置档案

定义模型架构、输出 horizon 与 Feature Contract 的组合。

每个 `.toml` 文件是一个独立的配置档案：

```toml
[model]
family = "transformer"
feature_contract = "inputs/configs/features/mainline_11d_v1.toml"
label_mode = "close_to_close"
```

`input_dim`、特征顺序和 `seq_len` 不在 profile 手工维护，而由 Feature Contract 的
`output_columns` 派生。当前状态：`model_mtl.toml` 仅保留给 Transformer 推理；它不再定义训练、
增量训练或 checkpoint 策略。
