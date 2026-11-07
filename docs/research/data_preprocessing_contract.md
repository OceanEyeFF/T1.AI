# 主线训练数据预处理合同

> 特征名称、顺序、维度与序列长度由
> [Feature Contract](../architecture/feature_contract.md) 单独冻结；本文件只定义其后的质量筛查与缩放。

## 目标

主线模型只能消费在预测时点可获得、数值有限、且由训练窗口自身统计量变换过的特征。
本合同覆盖 sequence 数据集到周度 rolling 训练之间的输入处理，不定义标签、模型结构或交易执行。

## 固定顺序

```text
因果特征序列
  → 非有限值筛查（NaN / +inf / -inf）
  → 标签成熟日过滤
  → 仅训练窗口 fit robust scaler
  → transform 验证集与当周 OOS
  → 训练 / 预测
```

不得颠倒顺序，尤其不得对 train + valid + OOS 合并后拟合任何 clip、中心或尺度参数。

## 特征质量规则

- 任一时点、任一特征为 NaN、+inf 或 -inf 的 sequence sample 必须被剔除；不得静默填零。
- 标签缺失与特征缺失分开处理。标签由 horizon 成熟日和停牌规则管理；特征缺失代表模型输入不可用。
- 数据集构建时必须记录剔除样本数及逐特征非有限值数；周度训练报告还必须分别记录 train、valid、OOS 三个分区的质量报告。
- 若筛查后任一分区为空，训练必须失败，不能产出部分 OOS 结论。

## 归一化规则

每个周度重训窗口按 feature base 在全部训练样本和 sequence timestep 上拟合：

1. 按训练窗口 0.5% / 99.5% 分位数 clip；
2. 用 clip 后中位数中心化；
3. 用 `IQR / 1.349` 缩放；IQR 过小则回退到标准差，再过小则使用 1；
4. 用同一组参数变换 valid 与 OOS，绝不重新 fit。

这样既限制金融特征的重尾值，又避免 valid/OOS 的分布信息进入训练。

## 可复现性要求

每个 rolling 周的报告必须保存：

- 特征名及顺序；
- clip、中心、尺度与 fallback 标记；
- fit 的训练样本数；
- 三个分区的非有限值报告；
- 数据集 ID、标签模式、训练窗口和随机 seed。

数据集 ID 必须包含 train / valid / test parquet SHA-256 派生的内容指纹。预处理、
数据修订或样本剔除导致任一 split 改变时，旧 OOS 报告自动成为不同 dataset ID 的产物，
不得与新数据集混用。

任何缺少这些记录的模型产物不得进入 strict 比较或认证。
