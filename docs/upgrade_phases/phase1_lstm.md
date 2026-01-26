# Phase 1: LSTM 模型集成

**状态**：🔲 待开始
**预计周期**：1-2 周
**优先级**：P0

---

## 1. 目标

在现有框架中添加 LSTM 模型，建立统一的多模型接口，为后续融合打下基础。

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 1.1 | 定义统一模型接口协议 | P0 | 🔲 | `models/base.py` |
| 1.2 | 实现 LSTMPredictor 模型 | P0 | 🔲 | `models/lstm.py` |
| 1.3 | 添加 LSTM 配置文件 | P1 | 🔲 | `configs/model_lstm.yaml` |
| 1.4 | 创建 LSTM 训练脚本 | P1 | 🔲 | `scripts/train_lstm.py` |
| 1.5 | 模型对比评估工具 | P2 | 🔲 | `evaluation/model_compare.py` |
| 1.6 | 单元测试 | P1 | 🔲 | `tests/test_lstm.py` |

---

## 3. 详细设计

### 3.1 统一模型接口 (Task 1.1)

**文件**：`src/ashare_lab/models/base.py`

```python
from typing import Protocol
from dataclasses import dataclass
import torch

@dataclass
class ModelOutput:
    """统一模型输出格式"""
    pred_3d: torch.Tensor    # [batch_size]
    pred_5d: torch.Tensor    # [batch_size]
    pred_10d: torch.Tensor   # [batch_size]
    confidence: torch.Tensor | None = None  # [batch_size], 可选
    hidden_state: torch.Tensor | None = None  # 用于Stacking

class BasePredictor(Protocol):
    """模型协议 - 所有预测模型必须实现"""

    def forward(self, x: torch.Tensor) -> ModelOutput:
        """
        Args:
            x: [batch_size, seq_len, n_features]
        Returns:
            ModelOutput 包含三个时间跨度的预测
        """
        ...

    def predict(self, x: torch.Tensor) -> ModelOutput:
        """推理模式（禁用dropout等）"""
        ...
```

### 3.2 LSTM 模型实现 (Task 1.2)

**文件**：`src/ashare_lab/models/lstm.py`

```python
import torch
import torch.nn as nn
from .base import ModelOutput

class LSTMPredictor(nn.Module):
    """
    LSTM 多任务预测器

    架构:
    - 双向 LSTM 编码器
    - 三个独立回归头 (3D/5D/10D)
    """

    def __init__(
        self,
        input_dim: int = 11,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = True,
    ):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
        )

        # 双向则 hidden_dim * 2
        encoder_dim = hidden_dim * 2 if bidirectional else hidden_dim

        # 三个独立回归头
        self.head_3d = self._make_head(encoder_dim)
        self.head_5d = self._make_head(encoder_dim)
        self.head_10d = self._make_head(encoder_dim)

    def _make_head(self, input_dim: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> ModelOutput:
        """
        Args:
            x: [batch, seq_len, input_dim]
        Returns:
            ModelOutput
        """
        # LSTM 编码
        lstm_out, (h_n, c_n) = self.lstm(x)

        # 取最后时刻输出
        last_hidden = lstm_out[:, -1, :]  # [batch, hidden*2]

        # 三个回归头
        pred_3d = self.head_3d(last_hidden).squeeze(-1)
        pred_5d = self.head_5d(last_hidden).squeeze(-1)
        pred_10d = self.head_10d(last_hidden).squeeze(-1)

        return ModelOutput(
            pred_3d=pred_3d,
            pred_5d=pred_5d,
            pred_10d=pred_10d,
            hidden_state=last_hidden,  # 保存用于 Stacking
        )

    def predict(self, x: torch.Tensor) -> ModelOutput:
        self.eval()
        with torch.no_grad():
            return self.forward(x)
```

### 3.3 配置文件 (Task 1.3)

**文件**：`configs/model_lstm.yaml`

```yaml
model:
  type: "lstm"
  input_dim: 11
  hidden_dim: 128
  num_layers: 2
  dropout: 0.2
  bidirectional: true

training:
  batch_size: 64
  learning_rate: 1e-4
  weight_decay: 1e-5
  max_epochs: 100
  early_stopping_patience: 10
  loss_type: "l1"  # 或 "ic_aware"

scheduler:
  type: "reduce_on_plateau"
  patience: 5
  factor: 0.5
```

### 3.4 训练脚本 (Task 1.4)

**文件**：`scripts/train_lstm.py`

主要逻辑：
1. 加载配置和数据
2. 初始化 LSTMPredictor
3. 训练循环（与 train_mtl.py 类似）
4. 保存 checkpoint

### 3.5 对比评估 (Task 1.5)

**文件**：`src/ashare_lab/evaluation/model_compare.py`

```python
def compare_models(
    models: dict[str, BasePredictor],
    test_loader: DataLoader,
) -> pd.DataFrame:
    """
    对比多个模型的性能

    Returns:
        DataFrame with columns: model, horizon, ic, rank_ic, mae
    """
    results = []
    for name, model in models.items():
        metrics = evaluate_model(model, test_loader)
        for horizon in ["3d", "5d", "10d"]:
            results.append({
                "model": name,
                "horizon": horizon,
                "ic": metrics[f"ic_{horizon}"],
                "rank_ic": metrics[f"rank_ic_{horizon}"],
                "mae": metrics[f"mae_{horizon}"],
            })
    return pd.DataFrame(results)
```

---

## 4. 验收标准

### 4.1 功能验收

- [ ] `LSTMPredictor` 可正常实例化和前向传播
- [ ] 输出格式与 `MTLTransformer` 一致（符合 `ModelOutput`）
- [ ] 训练脚本正常运行，checkpoint 正确保存
- [ ] 单元测试全部通过

### 4.2 性能验收

- [ ] LSTM 验证集 IC > 0.04
- [ ] 训练时间 < Transformer 的 1.5 倍
- [ ] 推理速度 > Transformer

---

## 5. 依赖与风险

### 依赖

- 现有数据加载模块：`dataset/sequence_parquet.py`
- 现有训练框架：`training/trainer.py`

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| LSTM 效果不如 Transformer | 中 | 调参优化；即使效果差也可作为融合成员 |
| 训练不稳定 | 低 | 梯度裁剪；学习率衰减 |

---

## 6. 后续步骤

完成 Phase 1 后：
1. 记录 LSTM vs Transformer 的对比结果
2. 进入 Phase 2（因子扩展）或 Phase 5（融合）
