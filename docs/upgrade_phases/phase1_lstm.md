# Phase 1: LSTM 模型替代

**状态**：🔲 待开始
**预计周期**：1-2 周
**优先级**：P1

---

## 1. 目标

**用 LSTM 模型替代现有 Transformer，选择更适合时间序列预测的成熟架构。**

### 1.1 为什么选择 LSTM 替代？

- ✅ **成熟的时间序列预测方案**（大量成功先例，网络资料丰富）
- ✅ **架构更简洁**（单模型，易维护，降低复杂度）
- ✅ **训练和推理更快**（相比 Transformer 的自注意力机制）
- ✅ **参数量更少**（降低过拟合风险）
- ✅ **无需模型融合**（避免无先例路径的风险）

### 1.2 替代策略说明

- **直接替换**：LSTM 完全取代 MTLTransformer
- **验证标准**：LSTM IC ≥ Transformer IC × 0.95 才正式切换
- **回退机制**：如果效果不佳，可回退到 Transformer

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 1.1 | 实现 LSTMPredictor 模型 | P0 | 🔲 | `models/lstm.py` |
| 1.2 | 添加 LSTM 配置文件 | P0 | 🔲 | `configs/model_lstm.yaml` |
| 1.3 | 创建 LSTM 训练脚本 | P0 | 🔲 | `scripts/train_lstm.py` |
| 1.4 | LSTM vs Transformer 对比验证 | P0 | 🔲 | 对比报告 + 切换决策 |
| 1.5 | 单元测试 | P1 | 🔲 | `tests/test_lstm.py` |
| 1.6 | 替换 MTL 训练脚本（可选） | P2 | 🔲 | `scripts/train_mtl.py` 更新 |

---

## 3. 详细设计

### 3.1 LSTM 模型实现 (Task 1.1)

**文件**：`src/ashare_lab/models/lstm.py`

```python
import torch
import torch.nn as nn

class LSTMPredictor(nn.Module):
    """
    LSTM 多任务预测器（替代 MTLTransformer）

    架构:
    - 双向 LSTM 编码器
    - 三个独立回归头 (3D/5D/10D)

    设计理念:
    - 保持与 MTLTransformer 相同的输出格式（三元组）
    - 参数量更少，训练更快
    - 专为时间序列优化
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

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, input_dim]
        Returns:
            (pred_3d, pred_5d, pred_10d) - 与 MTLTransformer 输出格式相同
        """
        # LSTM 编码
        lstm_out, (h_n, c_n) = self.lstm(x)

        # 取最后时刻输出
        last_hidden = lstm_out[:, -1, :]  # [batch, hidden*2]

        # 三个回归头
        pred_3d = self.head_3d(last_hidden).squeeze(-1)
        pred_5d = self.head_5d(last_hidden).squeeze(-1)
        pred_10d = self.head_10d(last_hidden).squeeze(-1)

        return pred_3d, pred_5d, pred_10d
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

### 3.5 LSTM vs Transformer 对比验证 (Task 1.4)

**目的**：验证 LSTM 是否达到替代标准

**验证方法**：

```python
# scripts/compare_lstm_transformer.py

def compare_lstm_vs_transformer():
    """
    对比 LSTM 和 Transformer 的性能

    验证标准:
    - LSTM IC ≥ Transformer IC × 0.95
    - LSTM 训练时间 < Transformer × 1.5
    - LSTM 推理速度 > Transformer
    """

    # 1. 加载两个模型
    lstm_model = load_checkpoint("models/best_lstm.pt")
    transformer_model = load_checkpoint("models/best_mtl.pt")

    # 2. 在相同测试集上评估
    test_loader = load_test_data()

    lstm_metrics = evaluate_model(lstm_model, test_loader)
    transformer_metrics = evaluate_model(transformer_model, test_loader)

    # 3. 生成对比报告
    report = {
        "lstm": {
            "ic_3d": lstm_metrics["ic_3d"],
            "ic_5d": lstm_metrics["ic_5d"],
            "ic_10d": lstm_metrics["ic_10d"],
            "avg_ic": lstm_metrics["avg_ic"],
            "train_time": lstm_metrics["train_time"],
            "inference_time": lstm_metrics["inference_time"],
        },
        "transformer": {
            "ic_3d": transformer_metrics["ic_3d"],
            "ic_5d": transformer_metrics["ic_5d"],
            "ic_10d": transformer_metrics["ic_10d"],
            "avg_ic": transformer_metrics["avg_ic"],
            "train_time": transformer_metrics["train_time"],
            "inference_time": transformer_metrics["inference_time"],
        },
        "verdict": "approve" if lstm_metrics["avg_ic"] >= transformer_metrics["avg_ic"] * 0.95 else "reject"
    }

    return report
```

**决策标准**：
- ✅ **通过**：LSTM 平均 IC ≥ Transformer × 0.95 → 正式切换到 LSTM
- ❌ **不通过**：LSTM 效果不佳 → 回退到 Transformer，Phase 1 失败

---

## 4. 验收标准

### 4.1 功能验收

- [ ] `LSTMPredictor` 可正常实例化和前向传播
- [ ] 输出格式与 `MTLTransformer` 完全一致（三元组）
- [ ] 训练脚本正常运行，checkpoint 正确保存
- [ ] 单元测试全部通过

### 4.2 性能验收（关键）

- [ ] **LSTM 平均 IC ≥ Transformer IC × 0.95**（替代标准）
- [ ] LSTM 验证集 IC > 0.04（绝对下限）
- [ ] 训练时间 < Transformer 的 1.5 倍
- [ ] 推理速度 ≥ Transformer

### 4.3 替代决策

| 条件 | 决策 | 后续动作 |
|------|------|---------|
| LSTM IC ≥ Transformer × 0.95 | ✅ **正式切换** | 更新 `scripts/train_mtl.py` 使用 LSTM |
| LSTM IC < Transformer × 0.95 | ❌ **保持 Transformer** | Phase 1 失败，分析原因 |
| LSTM IC 在 0.90-0.95 之间 | 🟡 **可选切换** | 权衡速度与精度后决定 |

---

## 5. 依赖与风险

### 依赖

- 现有数据加载模块：`dataset/sequence_parquet.py`
- 现有训练框架：`training/trainer.py`

### 风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LSTM 效果不如 Transformer × 0.95 | 中 | 高 | **回退机制**：保留 Transformer，Phase 1 失败但不影响后续 |
| LSTM 效果略差但可接受（0.90-0.95） | 低 | 中 | 权衡速度与精度，可能接受小幅下降 |
| 训练不稳定（梯度爆炸/消失） | 低 | 低 | 梯度裁剪；LSTM 天然对梯度稳定 |
| 超参数调优耗时 | 中 | 低 | 参考成熟 LSTM 配置；网格搜索 |

---

## 6. 后续步骤

### Phase 1 完成后的路径

#### ✅ 如果 LSTM 替代成功（IC ≥ Transformer × 0.95）

1. **记录对比结果**：生成完整的 LSTM vs Transformer 对比报告
2. **正式切换**：更新 `scripts/train_mtl.py` 默认使用 LSTM
3. **进入 Phase 2**：开始高级因子工程（APM/资金流）
4. **核心路径**：Phase 0 ✅ → Phase 2 → **Phase 1 ✅**（完成）

#### ❌ 如果 LSTM 替代失败（IC < Transformer × 0.95）

1. **分析失败原因**：
   - 超参数调优不足？
   - LSTM 架构不适合该数据？
   - 训练数据量不够？

2. **决策**：
   - **Option A**：调优 LSTM 继续尝试（额外 3-5 天）
   - **Option B**：保持 Transformer，Phase 1 失败
   - **Option C**：考虑其他架构（GRU、TCN 等）

3. **不影响后续**：Phase 2（因子扩展）仍可继续，不依赖 Phase 1

---

## 7. 与其他 Phase 的关系

- **Phase 0**（基础系统）：✅ 前置依赖，必须完成
- **Phase 2**（因子扩展）：🔀 并行关系，互不依赖
- **Phase 5**（模型融合）：❌ **已取消**（替代策略不需要融合）
- **Phase 3/4**（情绪/LLM）：🔵 可选，Phase 1 成功与否都不影响
