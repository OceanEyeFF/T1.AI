# Feature Contract：训练与推理的统一输入契约

## 目的

Feature Contract 是数据集构建、rolling 训练、日频推理和 checkpoint 的唯一输入语义来源。它锁定特征名称、顺序、参数、序列长度、输入维度和非有限值策略，避免“维度相同但特征语义不同”的静默误配。

当前主线契约：`inputs/configs/features/mainline_11d_v1.toml`。

## 字段

`[contract]` 必须包含：

- `id`、`version`：不可变版本标识；
- `seq_len`：训练与推理共同的序列长度；
- `expected_input_dim`：人工可读断言；实际 `input_dim` 始终由全部 `output_columns` 数量派生；
- `missing_value_policy = "reject_nonfinite"`：不允许零填充或截断来伪造可用输入。

每个 `[[features]]` 必须包含 `id`、白名单 `factory`、`params` 和有序 `output_columns`。Factory 的实际输出列必须与 Contract 完全相同，否则启动失败。

## 运行链路

```text
Feature Contract TOML
  → FeatureFactory
  → 数据集 metadata（ID / hash / names / input_dim / seq_len）
  → rolling LSTM / XGBoost
  → checkpoint manifest（模型家族、架构、label、scaler）
  → 日频推理严格加载
```

数据集构建会丢弃含非有限特征的 sequence sample；推理会排除含非有限特征的 symbol，绝不使用零向量替代。两者均遵循同一个 `reject_nonfinite` 语义。

## 兼容性规则

以下任一变化都必须创建新 Contract 版本，重建数据集并重新训练：

- 添加、删除或重排特征；
- 修改任何 feature factory 参数；
- 修改 `seq_len` 或缺失值策略。

Checkpoint 加载会校验 `model_family`、架构、Contract ID/hash、特征顺序、`input_dim`、`seq_len`、`label_mode` 和 scaler state。旧 checkpoint 没有 manifest 时会被拒绝，而不会采用宽松加载。

## 迁移

`load_sequence_parquet` 保留为 deprecated 兼容 shim，供外部调用方迁移；它不再静默将 NaN/Inf 填为零。旧数据集、旧 OOS 报告和旧 checkpoint 都没有 Feature Contract 身份，不能用于严格比较、认证或生产推理。
