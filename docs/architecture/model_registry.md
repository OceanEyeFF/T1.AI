# 模型注册表规范

> MS-R2-001 | 2026-06-23

## ModelABC 接口

所有模型必须实现 `src/ashare_lab/models/base.py` 中的 `ModelABC`：

```python
class ModelABC(ABC):
    @abstractmethod
    def train(self, data: TrainingData) -> None: ...
    @abstractmethod
    def predict(self, data: PredictionData) -> Result: ...
    @abstractmethod
    def save(self, path: Path) -> None: ...
    @abstractmethod
    def load(self, path: Path) -> None: ...
```

## 注册模型

当前已注册：`['lstm', 'transformer', 'xgboost']`

```python
from ashare_lab.models import create_model

# 通过名称创建
model = create_model("transformer", d_model=256, n_heads=8)

# 通过 TOML 配置创建
model = create_model_from_toml("inputs/configs/profiles/model_mtl.toml")
```

## 模型自包含规范

每个模型子文件夹结构：

```
src/ashare_lab/models/<model_name>/
├── __init__.py          # 实现 ModelABC 的模型类
├── config.toml          # 默认配置（超参、维度等）
└── (optional) _backend.py  # 底层实现（如 _mtl_transformer.py）
```

Checkpoint 保存到 `workspace/checkpoints/<model_name>_<variant>.pt`，不在模型代码目录中。

## 当前模型清单

| 模型 | 文件 | 特点 |
|------|------|------|
| Transformer | `transformer/__init__.py` (wrapper) + `_mtl_transformer.py` | MTL 多头输出，EarlyStoppingIC |
| LSTM | `lstm/__init__.py` | MtlLSTM + LSTMModel，4种 loss_type，RMSNorm/LayerNorm |
| XGBoost | `xgboost/__init__.py` | 每 horizon 独立 XGBRegressor |

## 向后兼容

旧的 import 路径保留为 re-export 层：

```python
# 仍然可用（指向 transformer/__init__.py）
from ashare_lab.models.transformer import create_mtl_model, MTLTransformer, EarlyStoppingIC
```
