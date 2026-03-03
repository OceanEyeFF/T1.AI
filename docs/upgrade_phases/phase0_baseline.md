# Phase 0: 基础系统完成

**状态**：🔴 待开始（最高优先级）
**预计周期**：3-5 天
**优先级**：P0（必须完成）

---

## 1. 目标

**打通端到端流程，验证当前系统效果**

当前系统虽然完成了 85% 的基础模块，但 **关键链路未打通**：
- ❌ 无法从原始数据生成训练序列
- ❌ 无法训练模型
- ❌ 无法生成推荐榜单
- ❌ 无法验证推荐效果

本阶段目标：补齐缺失环节，实现 **数据 → 训练 → 推荐 → 验证** 完整流程。

---

## 2. 核心缺口分析

| 模块 | 现状 | 缺口 | 影响 |
|------|------|------|------|
| 序列构建 | 0% | `SequenceDatasetBuilder` | 无法生成训练数据 |
| 推荐引擎 | 0% | `RecommendationEngine` | 无法输出推荐 |
| 训练脚本 | 30% | 端到端训练流程 | 无法训练模型 |
| 推荐验证 | 0% | `RecommendationValidator` | 无法评估效果 |

---

## 3. 任务清单

| ID | 任务 | 优先级 | 工作量 | 产出 |
|----|------|--------|--------|------|
| 0.1 | 序列数据集构建器 | P0 | 1天 | `dataset/sequence_builder.py` |
| 0.2 | 推荐引擎核心逻辑 | P0 | 1天 | `recommendation/engine.py` |
| 0.3 | MTL 训练脚本 | P0 | 1-2天 | `scripts/train_mtl.py` |
| 0.4 | 推荐验证器 | P1 | 0.5天 | `recommendation/validator.py` |
| 0.5 | 推荐历史管理 | P2 | 0.5天 | `recommendation/history.py` |
| 0.6 | 端到端集成测试 | P0 | 0.5天 | 验证完整流程 |

---

## 4. 详细设计

### 4.1 序列数据集构建器 (Task 0.1)

**文件**：`src/ashare_lab/dataset/sequence_builder.py`

**功能**：将特征矩阵转换为模型输入序列

```python
from dataclasses import dataclass
import pandas as pd
import torch
from torch.utils.data import Dataset

@dataclass
class SequenceConfig:
    seq_len: int = 30          # 序列长度（30日历史）
    horizons: tuple = (3, 5, 10)  # 预测时间跨度
    stride: int = 1            # 滑动窗口步长

class SequenceDataset(Dataset):
    """
    时序序列数据集

    输入：特征 DataFrame（MultiIndex: date, symbol）
    输出：[seq_len, n_feat] 序列 + 标签
    """

    def __init__(
        self,
        features: pd.DataFrame,
        labels: pd.DataFrame,
        config: SequenceConfig,
    ):
        self.config = config
        self.samples = self._build_samples(features, labels)

    def _build_samples(
        self,
        features: pd.DataFrame,
        labels: pd.DataFrame,
    ) -> list[dict]:
        """
        构建样本列表

        核心逻辑：
        1. 按股票分组
        2. 对每只股票，滑动窗口切分序列
        3. 确保 t 日标签不使用 t 日特征（防止泄露）
        """
        samples = []

        for symbol, group_feat in features.groupby(level="symbol"):
            # 获取对应标签
            try:
                group_label = labels.loc[(slice(None), symbol), :]
            except KeyError:
                continue

            # 滑动窗口
            for i in range(self.config.seq_len, len(group_feat), self.config.stride):
                # 特征：[i-seq_len : i]（不包含 i 日）
                feat_seq = group_feat.iloc[i - self.config.seq_len : i].values

                # 标签：i 日的未来收益
                try:
                    label_row = group_label.iloc[i]
                    label_vec = label_row[[f"label_{h}d" for h in self.config.horizons]].values
                except (IndexError, KeyError):
                    continue

                # 检查有效性
                if feat_seq.shape[0] < self.config.seq_len:
                    continue  # 序列不足

                samples.append({
                    "features": torch.tensor(feat_seq, dtype=torch.float32),
                    "labels": torch.tensor(label_vec, dtype=torch.float32),
                    "date": group_feat.index.get_level_values("date")[i],
                    "symbol": symbol,
                })

        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        return sample["features"], sample["labels"], sample["date"], sample["symbol"]


def build_sequence_dataset(
    data_config: dict,
    seq_config: SequenceConfig,
    save_dir: Path,
):
    """
    端到端数据集构建流程

    输入：data_config（数据源配置）
    输出：train/valid/test.pt（序列数据集）
    """
    # 1. 加载原始数据
    symbols = load_symbol_list(data_config["universe"])
    ohlcv_data = load_ohlcv_data(symbols, data_config)

    # 2. 计算特征
    feature_builder = FeatureBuilder(data_config["features"])
    features = feature_builder.build_all(ohlcv_data)

    # 3. 计算标签
    label_builder = MultiHorizonLabel(horizons=seq_config.horizons)
    labels = label_builder.compute(ohlcv_data)

    # 4. 划分训练/验证/测试集（Walk-Forward）
    train_dates = features.index.get_level_values("date") < "2023-01-01"
    valid_dates = (features.index.get_level_values("date") >= "2023-01-01") & \
                  (features.index.get_level_values("date") < "2024-01-01")
    test_dates = features.index.get_level_values("date") >= "2024-01-01"

    # 5. 构建序列数据集
    train_dataset = SequenceDataset(
        features[train_dates],
        labels[train_dates],
        seq_config,
    )
    valid_dataset = SequenceDataset(
        features[valid_dates],
        labels[valid_dates],
        seq_config,
    )
    test_dataset = SequenceDataset(
        features[test_dates],
        labels[test_dates],
        seq_config,
    )

    # 6. 保存
    save_dir.mkdir(parents=True, exist_ok=True)
    torch.save(train_dataset, save_dir / "train.pt")
    torch.save(valid_dataset, save_dir / "valid.pt")
    torch.save(test_dataset, save_dir / "test.pt")

    print(f"Dataset saved: {len(train_dataset)} train, {len(valid_dataset)} valid, {len(test_dataset)} test")
```

---

### 4.2 推荐引擎 (Task 0.2)

**文件**：`src/ashare_lab/recommendation/engine.py`

```python
from dataclasses import dataclass
from typing import List
import pandas as pd
import torch

@dataclass
class Recommendation:
    """单条推荐"""
    rank: int                # 排名 1-10
    symbol: str              # 股票代码
    name: str                # 股票名称
    predicted_return: float  # 预测收益率
    confidence: float        # 置信度
    reason: str              # 推荐理由

class RecommendationEngine:
    """
    推荐引擎

    输入：模型、特征构建器、股票池
    输出：3 个独立 Top-10 榜单（3D/5D/10D）
    """

    def __init__(
        self,
        model: torch.nn.Module,
        feature_builder: FeatureBuilder,
        universe_filter: UniverseFilter,
        seq_len: int = 30,
    ):
        self.model = model
        self.feature_builder = feature_builder
        self.universe_filter = universe_filter
        self.seq_len = seq_len

        self.model.eval()  # 推理模式

    def generate_recommendations(
        self,
        date: str,  # YYYYMMDD
        top_n: int = 10,
    ) -> dict[str, List[Recommendation]]:
        """
        生成多时间跨度推荐榜单

        Returns:
            {
                "3d": [Top 10 for 3-day],
                "5d": [Top 10 for 5-day],
                "10d": [Top 10 for 10-day],
            }
        """
        # 1. 获取股票池
        symbols = self.universe_filter.get_tradable_symbols(date)

        # 2. 构建特征序列
        sequences = []
        valid_symbols = []

        for symbol in symbols:
            # 获取 [date - seq_len, date) 的历史数据
            ohlcv = load_historical_data(symbol, date, lookback=self.seq_len)
            if len(ohlcv) < self.seq_len:
                continue  # 数据不足

            # 计算特征
            features = self.feature_builder.build_single(ohlcv)
            if features.isna().any():
                continue  # 特征缺失

            sequences.append(torch.tensor(features.values, dtype=torch.float32))
            valid_symbols.append(symbol)

        if len(sequences) == 0:
            return {"3d": [], "5d": [], "10d": []}

        # 3. 批量推理
        x = torch.stack(sequences)  # [N, seq_len, n_feat]

        with torch.no_grad():
            predictions = self.model(x)

        # predictions = {
        #     "pred_3d": Tensor([N]),
        #     "pred_5d": Tensor([N]),
        #     "pred_10d": Tensor([N]),
        # }

        # 4. 分别对 3 个预测任务排序
        recommendations = {}

        for horizon in ["3d", "5d", "10d"]:
            pred_key = f"pred_{horizon}"
            pred_values = predictions[pred_key].numpy()

            # 排序（降序）
            sorted_indices = pred_values.argsort()[::-1][:top_n]

            # 生成推荐列表
            recs = []
            for rank, idx in enumerate(sorted_indices, start=1):
                symbol = valid_symbols[idx]
                pred_ret = pred_values[idx]

                # 提取推荐理由
                reason = self._extract_reason(symbol, features)

                recs.append(Recommendation(
                    rank=rank,
                    symbol=symbol,
                    name=get_stock_name(symbol),
                    predicted_return=pred_ret,
                    confidence=0.8,  # TODO: 基于历史 IC 计算
                    reason=reason,
                ))

            recommendations[horizon] = recs

        return recommendations

    def _extract_reason(self, symbol: str, features: pd.DataFrame) -> str:
        """
        提取推荐理由（关键特征）

        示例：
        - "强势动量（20日+18%）"
        - "RSI=75 超买但仍强势"
        - "成交量放大 1.5 倍"
        """
        reasons = []

        # 动量特征
        if features.get("return_20d", 0) > 0.15:
            reasons.append(f"20日动量强劲（{features['return_20d']:.1%}）")

        # RSI
        if features.get("rsi_14", 0) > 70:
            reasons.append(f"RSI={features['rsi_14']:.0f} 超买强势")

        # 成交量
        if features.get("volume_ratio", 0) > 1.5:
            reasons.append(f"成交量放大 {features['volume_ratio']:.1f}x")

        return " | ".join(reasons) if reasons else "技术面向好"
```

---

### 4.3 MTL 训练脚本 (Task 0.3)

**文件**：`scripts/train_mtl.py`

```python
#!/usr/bin/env python
"""
MTL Transformer 训练脚本
"""
import argparse
from pathlib import Path
import torch
from torch.utils.data import DataLoader
import yaml

from ashare_lab.models.transformer import create_mtl_model
from ashare_lab.training.trainer import Trainer
from ashare_lab.evaluation.metrics import compute_ic

def main(args):
    # 1. 加载配置
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # 2. 加载数据集
    train_dataset = torch.load(args.data_dir / "train.pt")
    valid_dataset = torch.load(args.data_dir / "valid.pt")
    test_dataset = torch.load(args.data_dir / "test.pt")

    train_loader = DataLoader(
        train_dataset,
        batch_size=config["training"]["batch_size"],
        shuffle=True,
        num_workers=4,
    )
    valid_loader = DataLoader(valid_dataset, batch_size=64, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    # 3. 创建模型
    model = create_mtl_model(
        input_dim=config["model"]["input_dim"],
        d_model=config["model"]["d_model"],
        n_layers=config["model"]["n_layers"],
        n_heads=config["model"]["n_heads"],
        d_ff=config["model"]["d_ff"],
        dropout=config["model"]["dropout"],
        min_seq_len=config["model"]["min_seq_len"],
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    print(f"Model: {sum(p.numel() for p in model.parameters()):,} parameters")

    # 4. 训练器
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        valid_loader=valid_loader,
        config=config["training"],
        device=device,
    )

    # 5. 训练
    history = trainer.train()

    # 6. 测试集评估
    test_metrics = evaluate(model, test_loader, device)

    print("\n=== Test Set Metrics ===")
    for horizon in ["3d", "5d", "10d"]:
        print(f"{horizon}: IC={test_metrics[f'ic_{horizon}']:.4f}, "
              f"Rank IC={test_metrics[f'rank_ic_{horizon}']:.4f}")

    # 7. 保存模型
    save_dir = Path(config.get("save_dir", "models"))
    save_dir.mkdir(parents=True, exist_ok=True)

    torch.save({
        "model_state_dict": model.state_dict(),
        "config": config,
        "history": history,
        "test_metrics": test_metrics,
    }, save_dir / "best_mtl.pt")

    print(f"\nModel saved to {save_dir / 'best_mtl.pt'}")


def evaluate(model, dataloader, device):
    """评估模型"""
    model.eval()

    all_preds = {"3d": [], "5d": [], "10d": []}
    all_labels = {"3d": [], "5d": [], "10d": []}

    with torch.no_grad():
        for features, labels, _, _ in dataloader:
            features = features.to(device)
            predictions = model(features)

            for i, horizon in enumerate(["3d", "5d", "10d"]):
                pred_key = f"pred_{horizon}"
                all_preds[horizon].extend(predictions[pred_key].cpu().numpy())
                all_labels[horizon].extend(labels[:, i].numpy())

    # 计算 IC
    metrics = {}
    for horizon in ["3d", "5d", "10d"]:
        ic = compute_ic(all_preds[horizon], all_labels[horizon])
        rank_ic = compute_ic(all_preds[horizon], all_labels[horizon], method="spearman")
        metrics[f"ic_{horizon}"] = ic
        metrics[f"rank_ic_{horizon}"] = rank_ic

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/model_mtl.yaml")
    parser.add_argument("--data-dir", type=Path, default=Path("data/datasets"))
    args = parser.parse_args()

    main(args)
```

**运行命令：**

```bash
# 1. 构建数据集
python scripts/build_sequence_dataset.py --config configs/data_source.yaml

# 2. 训练模型
python scripts/train_mtl.py --config configs/model_mtl.yaml

# 3. 生成推荐
python scripts/generate_recommendations.py --date 20250115 --model models/best_mtl.pt
```

---

### 4.4 推荐验证器 (Task 0.4)

**文件**：`src/ashare_lab/recommendation/validator.py`

```python
class RecommendationValidator:
    """
    推荐验证器

    验证前一日推荐的准确性
    """

    def validate_recommendations(
        self,
        recommendations: dict[str, List[Recommendation]],
        actual_returns: pd.DataFrame,  # 实际收益
    ) -> dict:
        """
        验证推荐效果

        Returns:
            {
                "3d": {"hit_rate": 0.7, "avg_return": 0.023, "ic": 0.08},
                "5d": {"hit_rate": 0.75, "avg_return": 0.031, "ic": 0.09},
                "10d": {"hit_rate": 0.8, "avg_return": 0.048, "ic": 0.10},
            }
        """
        results = {}

        for horizon, recs in recommendations.items():
            symbols = [r.symbol for r in recs]
            pred_returns = [r.predicted_return for r in recs]

            # 获取实际收益
            actual = actual_returns.loc[symbols, f"return_{horizon}"]

            # 计算指标
            hit_rate = (actual > 0).sum() / len(actual)
            avg_return = actual.mean()
            ic = pd.Series(pred_returns).corr(actual)

            results[horizon] = {
                "hit_rate": hit_rate,
                "avg_return": avg_return,
                "ic": ic,
            }

        return results
```

---

## 5. 验收标准

### 5.1 功能验收

- [ ] 序列数据集构建器正常工作
  - [ ] 生成 train/valid/test 数据集
  - [ ] 无未来信息泄露（t 日标签不使用 t 日特征）
- [ ] 推荐引擎正常工作
  - [ ] 生成 3 个独立 Top-10 榜单
  - [ ] 推荐理由准确提取
- [ ] MTL 训练脚本正常工作
  - [ ] 训练成功完成
  - [ ] 模型 checkpoint 正确保存
- [ ] 推荐验证器正常工作
  - [ ] 准确计算命中率、平均收益、IC

### 5.2 性能验收

| 指标 | 目标 | 说明 |
|------|------|------|
| 验证集 IC | > 0.04 | 至少达到基准水平 |
| 命中率 | > 60% | Top-10 中上涨股票占比 |
| 平均收益 | > 沪深300 + 1% | Top-10 平均收益 |
| 训练时间 | < 2 小时 | 完整训练周期 |

---

## 6. 依赖与风险

### 依赖

- TuShare 数据源正常
- 现有特征/标签模块正常
- MTLTransformer 模型正常

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| 序列构建逻辑错误 | 中 | 单元测试、样本检查 |
| 模型训练不收敛 | 低 | 学习率调优、早停机制 |
| 推荐引擎性能瓶颈 | 低 | 批量推理、缓存优化 |

---

## 7. 后续步骤

完成 Phase 0 后：

1. **验证基准性能** - 记录当前系统 IC、命中率
2. **启动 Phase 2** - 添加高级因子（APM、资金流）
3. **持续监控** - 每日推荐效果追踪

---

**预计完成时间：** 3-5 天
**阻塞关系：** **所有后续 Phase 的前置条件**
**关键里程碑：** 首次生成推荐榜单并验证效果
