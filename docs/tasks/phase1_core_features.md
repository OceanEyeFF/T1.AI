# Phase 1: 核心功能补全

**预计工作量：** 3-5天
**优先级：** ⭐⭐⭐ 最高
**目标：** 实现端到端推荐系统MVP，生成首个3×Top-10推荐榜单

---

## 任务概览

| 任务ID | 任务名称 | 预计时间 | 依赖 | 状态 |
|--------|---------|---------|------|------|
| 1.1 | 序列数据集构建器 | 1天 | - | 🔲 待开始 |
| 1.2 | 推荐引擎核心逻辑 | 1天 | - | 🔲 待开始 |
| 1.3 | MTL训练脚本 | 1-2天 | 1.1 | 🔲 待开始 |
| 1.4 | 推荐输出格式化 | 0.5天 | 1.2 | 🔲 待开始 |
| 1.5 | 首次推荐榜单生成 | 0.5天 | 1.2, 1.3 | 🔲 待开始 |

---

## 任务1.1：序列数据集构建器 ⭐⭐⭐

**目标：** 将特征DataFrame转换为 `[batch, seq_len, n_feat]` 格式的序列数据集

### 交付物

- `src/ashare_lab/dataset/sequence_builder.py` - SequenceDatasetBuilder类
- `scripts/build_sequence_dataset.py` - 数据集构建脚本
- `tests/test_sequence_builder.py` - 单元测试

### 详细任务

#### 1.1.1 创建 SequenceDatasetBuilder 类

**代码位置：** `src/ashare_lab/dataset/sequence_builder.py`

**核心功能：**
```python
class SequenceDatasetBuilder:
    def __init__(self, seq_len: int = 30, stride: int = 1):
        """
        Args:
            seq_len: 序列长度（默认30日）
            stride: 滑动窗口步长（默认1日）
        """
        self.seq_len = seq_len
        self.stride = stride

    def build_sequences(
        self,
        features: pd.DataFrame,
        labels: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        构建序列数据集

        Args:
            features: [T, n_feat] - 特征DataFrame（日期索引）
            labels: [T, 3] - 标签DataFrame（包含label_3d/5d/10d）

        Returns:
            X: [N, seq_len, n_feat] - 特征序列
            y: [N, 3] - 标签（对应序列最后一日）
        """
        pass

    def split_walk_forward(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
    ) -> dict:
        """
        Walk-forward时间序列划分

        Returns:
            {
                "train": {"X": ..., "y": ...},
                "valid": {"X": ..., "y": ...},
                "test": {"X": ..., "y": ...},
            }
        """
        pass
```

**关键实现细节：**
- ✅ 严格时间对齐（t日特征对应t+N日标签）
- ✅ 处理NaN标签（保留mask供模型使用）
- ✅ Walk-forward划分（避免未来信息泄露）

#### 1.1.2 创建数据集构建脚本

**代码位置：** `scripts/build_sequence_dataset.py`

**功能：**
```python
def main():
    # Step 1: 加载特征和标签
    features = load_features(symbols, start_date, end_date)
    labels = load_labels(symbols, start_date, end_date)

    # Step 2: 构建序列
    builder = SequenceDatasetBuilder(seq_len=30)
    X, y = builder.build_sequences(features, labels)

    # Step 3: Walk-forward划分
    splits = builder.split_walk_forward(X, y)

    # Step 4: 保存为Parquet
    save_to_parquet(splits["train"], "data/datasets/train.parquet")
    save_to_parquet(splits["valid"], "data/datasets/valid.parquet")
    save_to_parquet(splits["test"], "data/datasets/test.parquet")

    # Step 5: 打印统计信息
    print(f"Train: {len(splits['train']['X'])} samples")
    print(f"Valid: {len(splits['valid']['X'])} samples")
    print(f"Test: {len(splits['test']['X'])} samples")
```

#### 1.1.3 编写单元测试

**代码位置：** `tests/test_sequence_builder.py`

**测试用例：**
- ✅ 序列长度验证
- ✅ 时间对齐验证（特征t对应标签t）
- ✅ NaN标签处理
- ✅ Walk-forward划分边界检查

**验收标准：**
- ✅ 所有测试通过
- ✅ 成功生成train/valid/test.parquet
- ✅ 数据集格式符合MTL模型输入要求

---

## 任务1.2：推荐引擎核心逻辑 ⭐⭐⭐

**目标：** 实现RecommendationEngine，生成3个独立的Top-10推荐榜单

### 交付物

- `src/ashare_lab/recommendation/` 目录结构
- `src/ashare_lab/recommendation/engine.py` - RecommendationEngine类
- `tests/test_recommendation_engine.py` - 单元测试

### 详细任务

#### 1.2.1 创建推荐引擎目录结构

```bash
mkdir -p src/ashare_lab/recommendation
touch src/ashare_lab/recommendation/__init__.py
touch src/ashare_lab/recommendation/engine.py
```

#### 1.2.2 实现 RecommendationEngine 类

**代码位置：** `src/ashare_lab/recommendation/engine.py`

**核心功能：**
```python
from dataclasses import dataclass

@dataclass
class Recommendation:
    rank: int                # 排名（1-10）
    symbol: str              # 股票代码
    name: str                # 股票名称
    predicted_return: float  # 预测收益率
    confidence: float        # 置信度（0-1）
    reason: str              # 推荐理由

class RecommendationEngine:
    def __init__(self, model, feature_builder, universe_filter):
        self.model = model
        self.feature_builder = feature_builder
        self.universe_filter = universe_filter

    def generate_recommendations(
        self,
        date: str,
        top_n: int = 10,
    ) -> dict[str, list[Recommendation]]:
        """
        生成3个独立推荐榜单

        Args:
            date: 推荐日期（YYYYMMDD）
            top_n: 推荐数量（默认10）

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
        features = self.feature_builder.build_sequences(symbols, date)

        # 3. 模型推理
        predictions = self.model(features)

        # 4. 分别对3个预测任务排序
        recommendations = {}
        for horizon in ["3d", "5d", "10d"]:
            pred_key = f"pred_{horizon}"
            sorted_stocks = self._rank_and_select(
                predictions[pred_key], symbols, top_n
            )
            recommendations[horizon] = sorted_stocks

        return recommendations

    def _extract_reason(self, symbol: str, features: dict) -> str:
        """提取推荐理由（关键特征）"""
        reasons = []

        # RSI判断
        if features["rsi_14"] > 70:
            reasons.append(f"RSI超买但仍强势({features['rsi_14']:.1f})")
        elif features["rsi_14"] > 50:
            reasons.append(f"RSI中性偏强({features['rsi_14']:.1f})")

        # 动量判断
        if features["return_20d"] > 0.15:
            reasons.append(f"20日动量强劲({features['return_20d']:.1%})")
        elif features["return_20d"] > 0.05:
            reasons.append(f"20日动量温和({features['return_20d']:.1%})")

        # 成交量判断
        if features["volume_ratio"] > 1.5:
            reasons.append(f"成交量放大({features['volume_ratio']:.2f}倍)")

        return " | ".join(reasons) if reasons else "技术指标综合评分较高"
```

#### 1.2.3 实现推荐输出格式化

**支持3种输出格式：**

1. **JSON格式：**
```python
def save_as_json(recommendations: dict, output_path: str):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "3d": [rec.to_dict() for rec in recommendations["3d"]],
        "5d": [rec.to_dict() for rec in recommendations["5d"]],
        "10d": [rec.to_dict() for rec in recommendations["10d"]],
    }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

2. **CSV格式：**
```python
def save_as_csv(recommendations: dict, output_dir: str):
    for horizon, recs in recommendations.items():
        df = pd.DataFrame([rec.to_dict() for rec in recs])
        df.to_csv(f"{output_dir}/recommendations_{horizon}.csv", index=False)
```

3. **Markdown格式：**
```python
def save_as_markdown(recommendations: dict, output_path: str):
    with open(output_path, "w") as f:
        f.write("# 多时间跨度股票推荐榜单\n\n")
        f.write(f"**日期：** {datetime.now().strftime('%Y-%m-%d')}\n\n")

        for horizon, recs in recommendations.items():
            f.write(f"## {horizon.upper()} 推荐（{horizon}）\n\n")
            f.write("| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |\n")
            f.write("|------|------|------|----------|--------|----------|\n")
            for rec in recs:
                f.write(f"| {rec.rank} | {rec.symbol} | {rec.name} | "
                       f"{rec.predicted_return:.2%} | {rec.confidence:.2f} | "
                       f"{rec.reason} |\n")
            f.write("\n")
```

#### 1.2.4 编写单元测试

**代码位置：** `tests/test_recommendation_engine.py`

**测试用例：**
- ✅ 推荐生成基础功能
- ✅ Top-N数量验证
- ✅ 3个时间跨度独立性验证
- ✅ 推荐理由提取测试

**验收标准：**
- ✅ 所有测试通过
- ✅ 成功生成3个Top-10榜单
- ✅ 输出格式正确（JSON/CSV/Markdown）

---

## 任务1.3：MTL训练脚本 ⭐⭐⭐

**目标：** 实现端到端MTL Transformer训练流程

### 交付物

- `scripts/train_mtl.py` - 完整训练脚本
- `configs/model_mtl.yaml` - 模型配置文件

### 详细任务

#### 1.3.1 创建模型配置文件

**代码位置：** `configs/model_mtl.yaml`

```yaml
# 模型架构配置
model:
  type: MTLTransformer
  input_dim: 10              # 特征数量（根据实际选择的特征调整）
  d_model: 128               # 隐藏层维度
  n_heads: 4                 # 注意力头数
  n_layers: 4                # Transformer层数
  d_ff: 512                  # 前馈网络维度
  dropout: 0.1               # Dropout比例
  min_seq_len: 30            # 最小序列长度
  max_seq_len: 60            # 最大序列长度
  loss_weights: [1.0, 1.0, 1.0]  # [3d, 5d, 10d]损失权重

# 训练超参数
training:
  batch_size: 32
  learning_rate: 1e-4
  weight_decay: 1e-5
  max_epochs: 50
  early_stopping_patience: 5
  early_stopping_metric: "val_ic"  # 验证集IC
  early_stopping_threshold: 0.05   # IC < 0.05触发早停

# 数据配置
data:
  seq_len: 30
  train_ratio: 0.7
  valid_ratio: 0.15
  test_ratio: 0.15

# 输出配置
output:
  model_dir: "models"
  log_dir: "logs"
  save_best_only: true
```

#### 1.3.2 创建训练脚本

**代码位置：** `scripts/train_mtl.py`

**核心流程：**
```python
import yaml
import torch
from pathlib import Path
from ashare_lab.models.transformer import create_mtl_model
from ashare_lab.dataset.sequence_builder import load_sequence_dataset

def main(config_path: str):
    # Step 1: 加载配置
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Step 2: 加载数据集
    train_data = load_sequence_dataset("data/datasets/train.parquet")
    valid_data = load_sequence_dataset("data/datasets/valid.parquet")

    # Step 3: 创建模型
    model = create_mtl_model(
        input_dim=config["model"]["input_dim"],
        d_model=config["model"]["d_model"],
        n_layers=config["model"]["n_layers"],
        n_heads=config["model"]["n_heads"],
        d_ff=config["model"]["d_ff"],
        dropout=config["model"]["dropout"],
        min_seq_len=config["model"]["min_seq_len"],
    )

    # Step 4: 训练循环
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )

    best_val_ic = -1.0
    patience_counter = 0

    for epoch in range(config["training"]["max_epochs"]):
        # 训练阶段
        train_loss = train_epoch(model, train_data, optimizer)

        # 验证阶段
        val_loss, val_ic = validate_epoch(model, valid_data)

        print(f"Epoch {epoch+1}/{config['training']['max_epochs']}")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Valid Loss: {val_loss:.4f}, IC: {val_ic:.4f}")

        # 早停检查
        if val_ic > best_val_ic:
            best_val_ic = val_ic
            patience_counter = 0
            torch.save(model.state_dict(), "models/best_mtl.pt")
            print("  ✅ Best model saved!")
        else:
            patience_counter += 1
            if patience_counter >= config["training"]["early_stopping_patience"]:
                print("Early stopping triggered!")
                break

    # Step 5: 测试集评估
    test_data = load_sequence_dataset("data/datasets/test.parquet")
    test_loss, test_ic = validate_epoch(model, test_data)
    print(f"\nTest Results: Loss={test_loss:.4f}, IC={test_ic:.4f}")

if __name__ == "__main__":
    main("configs/model_mtl.yaml")
```

**验收标准：**
- ✅ 训练成功完成（无报错）
- ✅ 验证集IC > 0.05
- ✅ 保存最佳模型checkpoint
- ✅ 打印训练日志（Loss/IC曲线）

---

## 任务1.4：推荐输出格式化 ⭐⭐

**目标：** 实现推荐结果的多格式输出

### 交付物

- JSON/CSV/Markdown格式输出（已集成在1.2中）

**验收标准：**
- ✅ 成功输出3种格式
- ✅ 格式正确、可读性强

---

## 任务1.5：首次推荐榜单生成 ⭐⭐⭐

**目标：** 验证端到端流程，生成首个3×Top-10推荐榜单

### 交付物

- `scripts/generate_daily_recommendations.py` - 推荐生成脚本
- 首个推荐榜单文件（JSON/CSV/Markdown）

### 详细任务

#### 1.5.1 创建推荐生成脚本

**代码位置：** `scripts/generate_daily_recommendations.py`

```python
from ashare_lab.recommendation.engine import RecommendationEngine
from ashare_lab.models.transformer import create_mtl_model
import torch

def main(date: str, model_path: str):
    # Step 1: 加载模型
    model = create_mtl_model(...)
    model.load_state_dict(torch.load(model_path))
    model.eval()

    # Step 2: 创建推荐引擎
    engine = RecommendationEngine(model, feature_builder, universe_filter)

    # Step 3: 生成推荐
    recommendations = engine.generate_recommendations(date, top_n=10)

    # Step 4: 保存输出
    save_as_json(recommendations, f"output/recommendations/{date}.json")
    save_as_markdown(recommendations, f"output/recommendations/{date}.md")

    print(f"✅ 推荐榜单已生成：{date}")

if __name__ == "__main__":
    main(date="20250115", model_path="models/best_mtl.pt")
```

#### 1.5.2 人工检查推荐结果

**检查清单：**
- ✅ 3个时间跨度都有10只股票
- ✅ 推荐股票符合股票池过滤规则（无ST/科创/创业）
- ✅ 预测收益率数值合理（不会出现±100%等异常值）
- ✅ 推荐理由合理（RSI/动量/成交量等特征匹配）

**验收标准：**
- ✅ 成功生成首个推荐榜单
- ✅ 人工检查通过（无明显异常）
- ✅ 端到端流程跑通

---

## Phase 1 总体验收标准

### 功能验收

- ✅ 序列数据集构建成功（train/valid/test.parquet）
- ✅ MTL Transformer训练成功（验证集IC > 0.05）
- ✅ 推荐引擎生成3×Top-10榜单
- ✅ 输出格式正确（JSON/CSV/Markdown）
- ✅ 所有单元测试通过（新增测试 ≥ 10个）

### 质量验收

- ✅ 代码符合项目规范（类型注解、文档字符串）
- ✅ 无明显Bug（能稳定运行3次以上）
- ✅ 性能合理（单次推荐生成 < 5分钟）

### 文档验收

- ✅ 更新主设计文档（反映已实现功能）
- ✅ 每个模块有README或文档字符串

---

## 下一步行动

完成Phase 1后，立即进入 **Phase 2: 验证与评估**

参见：[phase2_validation.md](./phase2_validation.md)
