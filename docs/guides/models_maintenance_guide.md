# models/ 模块维护指南

> 版本: 2026-06-23  
> 适用于: MS-R1-001 重构后的 `src/ashare_lab/models/` 模块

## 1. 模块架构

```
models/
├── __init__.py                # 公开 API + 自动发现
├── base.py                    # ModelABC + TrainingData/PredictionData/Result
├── registry.py                # 模型注册表（register_model / create_model / create_model_from_toml）
│
├── transformer/               # Transformer 模型
│   ├── __init__.py            #   TransformerModel(ModelABC) + 向后兼容导出
│   ├── _mtl_transformer.py    #   MTLTransformer nn.Module（原始实现）
│   └── config.toml            #   默认超参数
│
├── lstm/                      # LSTM 模型
│   ├── __init__.py            #   LSTMModel(ModelABC) + MtlLSTM nn.Module
│   └── config.toml            #   默认超参数
│
└── xgboost/                   # XGBoost 模型
    ├── __init__.py            #   XGBoostModel(ModelABC)
    └── config.toml            #   默认超参数
```

**三层架构**：模型层 ← 选股层（`PoolCandidate.symbols`） → 实验层（笛卡尔积评估）

## 2. 新增模型检查清单

### 2.1 创建子文件夹

```
models/<模型名>/
├── __init__.py    # 实现 ModelABC 子类 + 调用 register_model()
└── config.toml    # 默认超参数
```

### 2.2 规则

- [ ] 继承 `ModelABC` 并实现 `train/predict/save/load`
- [ ] 在 `__init__.py` 末尾调用 `register_model("模型名", 类名)`
- [ ] `config.toml` 包含 `[model]` section，`name` 字段等于注册名
- [ ] 子文件夹名 = 注册名（`model.name` 返回值）
- [ ] 不硬编码 `pred_cols`（通过构造函数参数传入）

### 2.3 代码模板

```python
from ashare_lab.models.base import ModelABC, TrainingData, TrainingResult, PredictionData, PredictionResult
from ashare_lab.models.registry import register_model

class MyModel(ModelABC):
    def __init__(self, *, pred_cols=("pred_3d","pred_5d","pred_10d"), **config):
        ...

    @property
    def name(self): return "mymodel"

    @property
    def description(self): return "描述"

    def train(self, data: TrainingData) -> TrainingResult: ...
    def predict(self, data: PredictionData) -> PredictionResult: ...
    def save(self, path): ...
    @classmethod
    def load(cls, path): ...

register_model("mymodel", MyModel)
```

### 2.4 使用方式

```python
# 方式 1：通过注册表
from ashare_lab.models import create_model
model = create_model("transformer", d_model=256, n_layers=4)

# 方式 2：通过 TOML 配置
from ashare_lab.models import create_model_from_toml
model = create_model_from_toml("models/transformer/config.toml", d_model=256)
```

## 3. 注册表 API

| 函数 | 用途 |
|---|---|
| `register_model(name, cls)` | 注册模型类 |
| `create_model(name, **config)` | 按名创建实例 |
| `create_model_from_toml(path, **overrides)` | 从 TOML 创建 |
| `get_model_class(name)` | 获取已注册类 |
| `list_registered_models()` | 列出所有注册模型 |

## 4. config.toml 格式

```toml
[model]
name = "模型名"           # 必填，等于 register_model 的 name
param1 = 0.5             # 模型参数
param2 = 128             # 模型参数
```

## 5. 禁止事项

- 在 `__init__.py` 写业务逻辑（只放模型类+注册调用）
- 硬编码 `pred_cols`（应通过 `__init__` 参数传入）
- 跨模型交叉导入
- 手动修改 `registry.py` 注册表（应通过 `register_model()` 自注册）

## 6. 向后兼容

Transformer 模型保留旧接口路径：

```python
from ashare_lab.models.transformer import create_mtl_model, MTLTransformer  # 仍可用
```
