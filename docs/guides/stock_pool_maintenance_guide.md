# stock_pools/ 模块维护指南

> 版本: 2026-06-23  
> 适用于: MS-R0-001 重构后的 `src/ashare_lab/stock_pool/` 模块

## 1. 模块架构

```
src/ashare_lab/stock_pool/
├── __init__.py                   # 公开导出：Strategy ABC + Registry API
├── base.py                       # StockPoolStrategy 抽象基类 + PoolCandidate
├── registry.py                   # 池子注册/校验/导出（格式冻结）
├── types.py                      # StockPoolRecord 数据类
│
├── low_manipulation/             # 策略：低控盘概率评分
│   ├── strategy.py               #   class LowManipulationStrategy(StockPoolStrategy)
│   ├── config.toml               #   策略参数（权重/阈值/参数）
│   └── pools/                    #   产出的 registry 池子 (.toml + .csv + .json)
│
├── momentum/                     # 占位：动量策略（待实现）
└── value/                        # 占位：价值策略（待实现）
```

**三层架构：**

| 层 | 职责 | 文件 |
|---|---|---|
| **选股层** | 策略 → 股票代码列表 | `stock_pools/<strategy>/strategy.py` |
| **训练层** | 拿代码，自己组织数据，训练模型 | `models/`, `dataset/` |
| **实验层** | 池子 × 模型笛卡尔积，回测评估 | `configs/experiments/`, `scripts/run_backtest.py` |

选股层不依赖训练层和实验层。

## 2. 新增策略检查清单

新增一个选股策略，按以下步骤操作：

### 2.1 创建策略子文件夹

```
stock_pools/<策略名>/
├── __init__.py      # 导出策略类
├── strategy.py      # 实现 StockPoolStrategy
├── config.toml      # 策略参数
└── pools/           # （初始为空，运行后产出池子文件）
```

### 2.2 规则

- [ ] **继承 `StockPoolStrategy`** — 所有策略必须实现其三个抽象成员
- [ ] **子文件夹名 = `strategy.name`** — 文件夹名必须和 name 属性一致
- [ ] **`__init__.py` 只做导出** — `from .strategy import XxxStrategy`，不写逻辑
- [ ] **`select()` 幂等** — 相同输入多次调用结果一致（随机种子固定）
- [ ] **`select()` 不接受 DataFrame** — 输入参数 `universe: list[str]`，不接收行情数据
- [ ] **返回 `PoolCandidate`** — symbols + metadata（含评分明细、排名、筛选依据）
- [ ] **不能导入训练层或实验层** — 选股层保持零下游依赖
- [ ] **config.toml 独立** — 参数外置，不硬编码在 strategy.py 里
- [ ] **pools/ 只放产物** — 不手写 TOML，通过 registry 导出

### 2.3 策略代码模板

```python
"""<策略中文描述>。"""

from __future__ import annotations

from ashare_lab.stock_pool.base import PoolCandidate, StockPoolStrategy


class NewStrategy(StockPoolStrategy):

    def __init__(self, param1: float = 1.0) -> None:
        self.param1 = param1

    # ---- 必须实现的抽象成员 ----

    @property
    def name(self) -> str:
        """策略唯一标识，作为文件夹名和 pool_family。"""
        return "new_strategy"

    @property
    def description(self) -> str:
        """一句话描述，出现在日志和报告中。"""
        return "一句话描述这个策略做了什么"

    def select(self, universe: list[str]) -> PoolCandidate:
        """从 universe 中按本策略逻辑筛选。"""
        selected = ...  # 你的选股逻辑
        return PoolCandidate(
            symbols=selected,
            metadata={
                "strategy": self.name,
                "total_scored": len(universe),
                "total_selected": len(selected),
                # 可附加评分明细、排名等
            },
        )
```

### 2.4 config.toml 格式

```toml
# <策略名> 配置

[strategy]
param1 = 1.0          # 对外暴露的可调参数
threshold = 60.0       # 入选阈值

# 参数注释说明每个字段的含义
[weights]
factor_a = 0.50       # A 因子权重
factor_b = 0.50       # B 因子权重
```

## 3. Registry 注册规则

策略产出的池子通过 `export_stock_pool_artifacts()` 注册到 `configs/stock_pools/`。

### 3.1 ID 命名

```
custom_<策略名>_v<版本号>
```

示例：

- `custom_low_manipulation_v1` — 低控盘评分 v1
- 未来：`custom_momentum_v1`, `custom_value_v1`

### 3.2 TOML 必填字段

| 字段 | 说明 | 示例 |
|---|---|---|
| `stock_pool_id` | 唯一 ID | `"custom_low_manipulation_v1"` |
| `stock_pool_version` | 版本号 | `"1"` |
| `pool_family` | 系列 | `"custom"` |
| `pool_label` | 显示名 | `"低控盘评分v1"` |
| `construction_method` | 构建方法 | `"6-dimension composite scoring"` |
| `base_universe` | 基础股票池 | `"main board A-shares (excl. 300/688/8/4)"` |
| `symbols_source` | 符号来源 | 相对路径或描述 |
| `symbols_count` | 股票数量 | 14 |
| `rebalance_frequency` | 再平衡频率 | `"monthly"` |
| `effective_start` | 生效日期 | `"2023-01-01"` |
| `effective_end` | 失效日期 | `"2026-03-31"` |
| `is_default` | 是否默认 | `false` |
| `is_research_only` | 是否仅研究 | `true`（Gate 通过前） |
| `owner` | 负责人/模块 | `"stock_pool/low_manipulation"` |
| `notes` | 备注 | 数据来源、窗口、依赖等 |

### 3.3 产出文件

注册后 `configs/stock_pools/` 下生成三个文件：

```
configs/stock_pools/
├── custom_low_manipulation_v1.toml          # registry 记录
├── custom_low_manipulation_v1_symbols.csv   # 股票列表
└── custom_low_manipulation_v1_metadata.json # 元数据
```

## 4. 禁止事项

| ❌ 禁止 | 原因 |
|---|---|
| 在 `strategy.py` 里硬编码股票代码 | 策略应是算法，不是静态列表 |
| 从数据集/模型模块导入 | 选股层不能依赖训练层 |
| 在 `__init__.py` 里写业务逻辑 | 只做导出，保持模块边界清晰 |
| 手动创建 `configs/stock_pools/*.toml` | 必须通过 registry API 导出，保证格式一致 |
| `select()` 签名加多余参数 | 统一接口：`(self, universe: list[str]) -> PoolCandidate` |
| `name` 用中文 | 英文，保持与文件夹名一致 |
| 策略文件夹嵌套子模块 | 一个策略 = 一个文件夹 = 一个 strategy.py |

## 5. 测试规范

新增策略必须附带测试：

```python
# tests/stock_pool/test_<策略名>_strategy.py

def test_strategy_implements_base():
    """必须继承 StockPoolStrategy。"""
    from ashare_lab.stock_pool.low_manipulation.strategy import LowManipulationStrategy
    from ashare_lab.stock_pool.base import StockPoolStrategy
    assert issubclass(LowManipulationStrategy, StockPoolStrategy)


def test_select_idempotent():
    """相同 universe 多次调用结果一致。"""
    ...


def test_select_returns_pool_candidate():
    """返回值类型正确。"""
    from ashare_lab.stock_pool.base import PoolCandidate
    s = LowManipulationStrategy()
    result = s.select(["600519", "000001"])
    assert isinstance(result, PoolCandidate)
    assert isinstance(result.symbols, list)
    assert isinstance(result.metadata, dict)


def test_select_no_data_leak():
    """select() 不修改传入的 universe。"""
    ...


def test_empty_universe():
    """空 universe 返回空结果。"""
    result = LowManipulationStrategy().select([])
    assert result.symbols == []
```

## 6. 修改现有策略

- **修改评分公式** → 改 `strategy.py` 的 `select()` 逻辑和 `config.toml`
- **修改变更阈值** → 只改 `config.toml`，不改代码
- **修改 ID** → 升级版本号（`v1` → `v2`），保留旧版本池子文件
- **删除旧版本** → 确认无下游引用后删除 TOML/CSV/JSON 三件套

## 7. 数据依赖

| 数据源 | 路径 | 谁在用 |
|---|---|---|
| QFQ 日线 | `inputs/data/cache/tushare_qfq/` | low_manipulation（所有指标） |
| 基本面 | `inputs/data/cache/tushare_daily_basic/` | low_manipulation（市值/换手率） |
| 资金流向 | `inputs/data/cache/tushare_moneyflow/` | low_manipulation（大单流向） |
| 指数行情 | `inputs/data/cache/tushare_qfq/510300.SH/` | low_manipulation（β/R² 计算） |

新策略如需其他数据，在策略文件夹内自建数据加载逻辑，不修改现有数据层。

## 8. 常见问题

**Q: 策略需要获取实盘数据怎么办？**  
A: 在 `select()` 内部调用 `data/` 模块。选股层可以读数据，但不能依赖训练/实验层模块。

**Q: 我的策略需要训练模型？**  
A: 那它不属于选股层，应放在 `models/`。选股层只做规则/评分/排序，不做预测训练。

**Q: 能否复用另一个策略的逻辑？**  
A: 不允许策略间交叉导入。提取公共逻辑到 `stock_pool/utils.py`，各策略分别引用。

**Q: `PoolCandidate.metadata` 应该放什么？**  
A: 评分明细、排名、各项指标值、筛选条件——这些是"为什么这些股票被选中"的证据。下游实验报告会引用。
