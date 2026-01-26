# Phase 5: 模型融合优化

**状态**：🔲 待开始
**预计周期**：2 周
**优先级**：P0

---

## 1. 目标

实现多模型融合机制，通过动态权重和 Stacking 提升整体预测性能。

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 5.1 | 特征融合器 | P0 | 🔲 | `fusion/feature_fuser.py` |
| 5.2 | 加权平均集成 | P0 | 🔲 | `fusion/weighted_ensemble.py` |
| 5.3 | 动态权重集成 | P1 | 🔲 | `fusion/dynamic_ensemble.py` |
| 5.4 | Stacking 元学习 | P2 | 🔲 | `fusion/stacking.py` |
| 5.5 | 决策融合器 | P1 | 🔲 | `fusion/decision_fuser.py` |
| 5.6 | 融合效果评估 | P1 | 🔲 | `evaluation/fusion_metrics.py` |
| 5.7 | 单元测试 | P1 | 🔲 | `tests/test_fusion.py` |

---

## 3. 详细设计

### 3.1 特征融合器 (Task 5.1)

**文件**：`src/ashare_lab/fusion/feature_fuser.py`

```python
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class FusionConfig:
    max_features: int = 50
    min_ic_threshold: float = 0.02
    max_correlation: float = 0.8

class FeatureFuser:
    """
    特征融合器

    职责：
    1. 收集所有因子输出
    2. IC 筛选 + 相关性去重
    3. 输出统一特征矩阵
    """

    def __init__(self, config: FusionConfig):
        self.config = config
        self.selected_features: list[str] = []

    def fit(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> "FeatureFuser":
        """
        拟合特征选择器
        """
        # 1. 计算各特征 IC
        ic_values = {}
        for col in features.columns:
            ic = self._compute_ic(features[col], labels)
            ic_values[col] = ic

        # 2. 过滤低 IC 特征
        valid = [
            col for col, ic in ic_values.items()
            if abs(ic) >= self.config.min_ic_threshold
        ]

        # 3. 相关性去重
        self.selected_features = self._remove_correlated(
            features[valid], ic_values
        )

        return self

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """提取选中的特征"""
        return features[self.selected_features]

    def _compute_ic(self, feature: pd.Series, label: pd.Series) -> float:
        """计算 IC"""
        from scipy.stats import spearmanr
        valid = ~(feature.isna() | label.isna())
        if valid.sum() < 100:
            return 0.0
        ic, _ = spearmanr(feature[valid], label[valid])
        return ic if not np.isnan(ic) else 0.0

    def _remove_correlated(
        self,
        features: pd.DataFrame,
        ic_values: dict[str, float],
    ) -> list[str]:
        """去除高相关特征"""
        corr = features.corr().abs()
        selected = []

        # 按 IC 降序
        sorted_features = sorted(
            features.columns,
            key=lambda x: abs(ic_values.get(x, 0)),
            reverse=True,
        )

        for feat in sorted_features:
            if len(selected) >= self.config.max_features:
                break

            # 检查与已选特征的相关性
            is_redundant = any(
                corr.loc[feat, sel] > self.config.max_correlation
                for sel in selected
                if feat in corr.index and sel in corr.columns
            )

            if not is_redundant:
                selected.append(feat)

        return selected
```

### 3.2 加权平均集成 (Task 5.2)

**文件**：`src/ashare_lab/fusion/weighted_ensemble.py`

```python
from .base import BaseEnsemble, ModelOutput
import torch
import numpy as np

class WeightedAverageEnsemble(BaseEnsemble):
    """
    加权平均集成

    权重基于验证集 IC
    """

    def __init__(
        self,
        model_names: list[str],
        horizons: list[str] = ["3d", "5d", "10d"],
    ):
        self.model_names = model_names
        self.horizons = horizons
        # 初始等权
        self.weights = {
            h: {name: 1.0 / len(model_names) for name in model_names}
            for h in horizons
        }

    def fit(
        self,
        predictions: dict[str, ModelOutput],  # {model_name: output}
        labels: torch.Tensor,  # [n_samples, 3]
    ) -> "WeightedAverageEnsemble":
        """基于 IC 学习权重"""
        for h_idx, horizon in enumerate(self.horizons):
            ics = {}
            for name, output in predictions.items():
                pred = getattr(output, f"pred_{horizon}")
                target = labels[:, h_idx]
                ic = self._compute_ic(pred, target)
                ics[name] = max(ic, 0.01)  # 最小权重

            # 归一化
            total = sum(ics.values())
            self.weights[horizon] = {
                name: ic / total for name, ic in ics.items()
            }

        return self

    def predict(
        self,
        predictions: dict[str, ModelOutput],
    ) -> ModelOutput:
        """加权融合"""
        fused = {}

        for horizon in self.horizons:
            weighted_sum = None
            for name, output in predictions.items():
                pred = getattr(output, f"pred_{horizon}")
                weight = self.weights[horizon][name]

                if weighted_sum is None:
                    weighted_sum = pred * weight
                else:
                    weighted_sum = weighted_sum + pred * weight

            fused[f"pred_{horizon}"] = weighted_sum

        return ModelOutput(**fused)

    def _compute_ic(self, pred: torch.Tensor, target: torch.Tensor) -> float:
        from scipy.stats import spearmanr
        p = pred.detach().cpu().numpy()
        t = target.detach().cpu().numpy()
        valid = ~(np.isnan(p) | np.isnan(t))
        if valid.sum() < 10:
            return 0.0
        ic, _ = spearmanr(p[valid], t[valid])
        return ic if not np.isnan(ic) else 0.0
```

### 3.3 动态权重集成 (Task 5.3)

**文件**：`src/ashare_lab/fusion/dynamic_ensemble.py`

```python
class DynamicWeightEnsemble(WeightedAverageEnsemble):
    """
    动态权重集成

    根据近期表现动态调整权重
    """

    def __init__(
        self,
        model_names: list[str],
        lookback: int = 20,
        decay: float = 0.95,
        min_weight: float = 0.05,
    ):
        super().__init__(model_names)
        self.lookback = lookback
        self.decay = decay
        self.min_weight = min_weight

        # 历史 IC 记录
        self.ic_history: dict[str, dict[str, list[float]]] = {
            h: {name: [] for name in model_names}
            for h in self.horizons
        }

    def update(
        self,
        predictions: dict[str, ModelOutput],
        realized_returns: dict[str, torch.Tensor],
    ) -> None:
        """
        每日更新权重

        在 T+N 日调用，验证 T 日预测
        """
        for horizon in self.horizons:
            for name, output in predictions.items():
                pred = getattr(output, f"pred_{horizon}")
                actual = realized_returns[horizon]
                ic = self._compute_ic(pred, actual)

                # 记录历史
                self.ic_history[horizon][name].append(ic)

                # 保留最近 N 天
                if len(self.ic_history[horizon][name]) > self.lookback:
                    self.ic_history[horizon][name].pop(0)

        # 重新计算权重
        self._recalculate_weights()

    def _recalculate_weights(self):
        """带时间衰减的权重计算"""
        for horizon in self.horizons:
            scores = {}

            for name in self.model_names:
                history = self.ic_history[horizon][name]
                if not history:
                    scores[name] = self.min_weight
                    continue

                # 衰减加权
                score = sum(
                    ic * (self.decay ** (len(history) - 1 - t))
                    for t, ic in enumerate(history)
                )
                scores[name] = max(score, self.min_weight)

            # 归一化
            total = sum(scores.values())
            self.weights[horizon] = {
                name: s / total for name, s in scores.items()
            }
```

### 3.4 Stacking 元学习 (Task 5.4)

**文件**：`src/ashare_lab/fusion/stacking.py`

```python
import torch
import torch.nn as nn

class StackingEnsemble(nn.Module):
    """
    Stacking 元学习集成

    使用元模型学习如何组合基模型预测
    """

    def __init__(
        self,
        n_models: int,
        hidden_dim: int = 128,
        horizons: list[str] = ["3d", "5d", "10d"],
    ):
        super().__init__()

        self.horizons = horizons

        # 元特征维度: 每个模型的预测 + hidden_state
        # 假设 hidden_dim=128, n_models=3
        # 则 input_dim = 3 * (3 + 128) = 393
        input_dim = n_models * (len(horizons) + hidden_dim)

        # 元模型
        self.meta_models = nn.ModuleDict({
            h: nn.Sequential(
                nn.Linear(input_dim, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )
            for h in horizons
        })

    def forward(
        self,
        model_outputs: list[ModelOutput],
    ) -> ModelOutput:
        """
        元模型预测
        """
        # 构建元特征
        meta_features = []
        for output in model_outputs:
            meta_features.append(output.pred_3d.unsqueeze(1))
            meta_features.append(output.pred_5d.unsqueeze(1))
            meta_features.append(output.pred_10d.unsqueeze(1))
            if output.hidden_state is not None:
                meta_features.append(output.hidden_state)

        meta_input = torch.cat(meta_features, dim=1)

        # 各 horizon 预测
        preds = {}
        for h in self.horizons:
            preds[f"pred_{h}"] = self.meta_models[h](meta_input).squeeze(-1)

        return ModelOutput(**preds)

    def fit(
        self,
        model_outputs: list[ModelOutput],
        labels: torch.Tensor,
        epochs: int = 50,
        lr: float = 1e-3,
    ):
        """训练元模型"""
        optimizer = torch.optim.Adam(self.parameters(), lr=lr)

        for epoch in range(epochs):
            self.train()

            pred = self.forward(model_outputs)

            # IC-aware 损失
            loss = 0
            for h_idx, h in enumerate(self.horizons):
                p = getattr(pred, f"pred_{h}")
                t = labels[:, h_idx]
                loss += self._ic_loss(p, t)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        return self

    def _ic_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """最大化 IC 的损失函数"""
        pred_std = (pred - pred.mean()) / (pred.std() + 1e-8)
        target_std = (target - target.mean()) / (target.std() + 1e-8)
        ic = (pred_std * target_std).mean()
        return 1 - ic
```

### 3.5 决策融合器 (Task 5.5)

**文件**：`src/ashare_lab/fusion/decision_fuser.py`

```python
@dataclass
class FinalRecommendation:
    symbol: str
    horizon: str
    predicted_return: float
    quant_confidence: float
    llm_adjustment: float
    final_confidence: float
    reasoning: str
    risk_level: str

class DecisionFuser:
    """
    决策融合器

    融合量化信号与 LLM 验证结果
    """

    def __init__(
        self,
        llm_validator: SignalValidator | None = None,
        llm_weight: float = 0.3,
        enable_veto: bool = True,
        min_confidence: float = 0.3,
    ):
        self.llm_validator = llm_validator
        self.llm_weight = llm_weight
        self.enable_veto = enable_veto
        self.min_confidence = min_confidence

    async def fuse(
        self,
        quant_signals: list[dict],
        market_context: dict,
    ) -> list[FinalRecommendation]:
        """
        融合量化信号与 LLM 验证
        """
        results = []

        for signal in quant_signals:
            # LLM 验证（如果启用）
            if self.llm_validator:
                validation = await self.llm_validator.validate(
                    signal, market_context
                )
                adjustment = validation.adjustment
                reasoning = validation.reasoning

                # 否决检查
                if self.enable_veto and validation.verdict == LLMVerdict.REJECT:
                    continue
            else:
                adjustment = 1.0
                reasoning = "无 LLM 验证"

            # 计算最终置信度
            quant_conf = signal["confidence"]
            final_conf = quant_conf * (1 + self.llm_weight * (adjustment - 1))
            final_conf = max(0.0, min(1.0, final_conf))

            # 过滤低置信度
            if final_conf < self.min_confidence:
                continue

            results.append(FinalRecommendation(
                symbol=signal["symbol"],
                horizon=signal["horizon"],
                predicted_return=signal["pred_return"],
                quant_confidence=quant_conf,
                llm_adjustment=adjustment,
                final_confidence=final_conf,
                reasoning=reasoning,
                risk_level=self._assess_risk(final_conf),
            ))

        # 按最终置信度排序
        results.sort(key=lambda x: x.final_confidence, reverse=True)
        return results

    def _assess_risk(self, confidence: float) -> str:
        if confidence >= 0.7:
            return "low"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "high"
```

### 3.6 融合效果评估 (Task 5.6)

**文件**：`src/ashare_lab/evaluation/fusion_metrics.py`

```python
@dataclass
class FusionReport:
    model_comparison: pd.DataFrame   # 各模型 IC 对比
    ensemble_metrics: dict           # 集成后指标
    fusion_gain: dict                # 融合增益
    llm_filter_effect: dict          # LLM 过滤效果

class FusionEvaluator:
    """
    融合效果评估器
    """

    def evaluate(
        self,
        single_predictions: dict[str, ModelOutput],
        ensemble_prediction: ModelOutput,
        labels: torch.Tensor,
    ) -> FusionReport:
        """评估融合效果"""

        # 1. 各模型 IC
        model_ics = {}
        for name, pred in single_predictions.items():
            model_ics[name] = {
                "ic_3d": self._compute_ic(pred.pred_3d, labels[:, 0]),
                "ic_5d": self._compute_ic(pred.pred_5d, labels[:, 1]),
                "ic_10d": self._compute_ic(pred.pred_10d, labels[:, 2]),
            }

        # 2. 集成 IC
        ensemble_ics = {
            "ic_3d": self._compute_ic(ensemble_prediction.pred_3d, labels[:, 0]),
            "ic_5d": self._compute_ic(ensemble_prediction.pred_5d, labels[:, 1]),
            "ic_10d": self._compute_ic(ensemble_prediction.pred_10d, labels[:, 2]),
        }

        # 3. 计算增益
        best_single = max(
            sum(ics.values()) / 3 for ics in model_ics.values()
        )
        ensemble_avg = sum(ensemble_ics.values()) / 3

        fusion_gain = {
            "best_single_ic": best_single,
            "ensemble_ic": ensemble_avg,
            "gain_pct": (ensemble_avg - best_single) / best_single * 100,
            "is_effective": ensemble_avg > best_single,
        }

        return FusionReport(
            model_comparison=pd.DataFrame(model_ics).T,
            ensemble_metrics=ensemble_ics,
            fusion_gain=fusion_gain,
            llm_filter_effect={},  # 需要实际数据
        )
```

---

## 4. 验收标准

### 4.1 功能验收

- [ ] 特征融合正常工作，输出维度符合预期
- [ ] 加权平均集成正确计算
- [ ] 动态权重根据历史 IC 正确更新
- [ ] Stacking 元模型可训练
- [ ] 决策融合器正确整合 LLM 结果

### 4.2 性能验收

| 指标 | 目标 |
|------|------|
| 融合 IC > 最优单模型 IC | ✅ |
| 融合增益 | > 5% |
| 命中率提升 | > 3% |

---

## 5. 依赖与风险

### 依赖

- Phase 1: LSTM 模型
- Phase 2-3: 高级因子
- Phase 4: LLM 验证

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| 融合无增益 | 中 | 检查模型相关性，确保多样性 |
| Stacking 过拟合 | 中 | 交叉验证，正则化 |
| 动态权重不稳定 | 低 | 设置最小权重，平滑更新 |

---

## 6. 后续步骤

完成 Phase 5 后：
1. 集成测试：端到端流程验证
2. 性能调优：超参数搜索
3. 上线准备：监控告警配置
