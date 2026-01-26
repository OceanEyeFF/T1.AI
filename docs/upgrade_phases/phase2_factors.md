# Phase 2: 高级因子工程

**状态**：🔲 待开始
**预计周期**：2-3 周
**优先级**：P0

---

## 1. 目标

扩展因子库，引入 APM 因子、资金流向因子和 GP 因子框架，提升信号质量。

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 2.1 | 实现 APM 因子 | P0 | 🔲 | `features/apm.py` |
| 2.2 | 北向资金数据源 | P1 | 🔲 | `data/northbound_source.py` |
| 2.3 | 资金流向因子 | P1 | 🔲 | `features/money_flow.py` |
| 2.4 | GP 因子框架设计 | P1 | 🔲 | `features/gp_mining/` |
| 2.5 | GP 因子挖掘实现 | P2 | 🔲 | `features/gp_mining/generator.py` |
| 2.6 | 因子有效性评估 | P1 | 🔲 | `evaluation/factor_analysis.py` |
| 2.7 | 单元测试 | P1 | 🔲 | `tests/test_new_factors.py` |

---

## 3. 详细设计

### 3.1 APM 因子 (Task 2.1)

**文件**：`src/ashare_lab/features/apm.py`

**原理**：
- 隔夜收益反映散户情绪（信息不对称）
- 盘中收益反映机构行为（知情交易）
- APM = 盘中收益 - 隔夜收益

```python
from .base import BaseFeature, FeatureMeta, NormalizationMethod

class APMFactor(BaseFeature):
    """
    APM 因子 (Asymmetric Price Movement)

    捕捉知情交易者的信息优势
    夏普比率预期: ~1.5
    """

    @property
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            name="apm",
            normalization=NormalizationMethod.RANK,
            clip_range=(-3.0, 3.0),
        )

    def compute_raw(self, data: dict[str, pd.DataFrame]) -> pd.Series:
        ohlcv = data["ohlcv"]

        # 隔夜收益: open[t] / close[t-1] - 1
        overnight_ret = ohlcv["open"] / ohlcv["close"].shift(1) - 1

        # 盘中收益: close[t] / open[t] - 1
        intraday_ret = ohlcv["close"] / ohlcv["open"] - 1

        # APM = 盘中 - 隔夜
        apm = intraday_ret - overnight_ret

        return apm
```

### 3.2 北向资金数据源 (Task 2.2)

**文件**：`src/ashare_lab/data/northbound_source.py`

```python
import akshare as ak
import pandas as pd
from dataclasses import dataclass

@dataclass
class NorthboundFlowRequest:
    start_date: str  # YYYYMMDD
    end_date: str

def fetch_northbound_flow(req: NorthboundFlowRequest) -> pd.DataFrame:
    """
    获取北向资金数据

    Returns:
        DataFrame with columns:
        - date: 日期
        - sh_net: 沪股通净流入
        - sz_net: 深股通净流入
        - total_net: 合计净流入
    """
    # 沪股通
    sh_df = ak.stock_hsgt_north_net_flow_in_em(symbol="沪股通")
    # 深股通
    sz_df = ak.stock_hsgt_north_net_flow_in_em(symbol="深股通")

    # 合并处理
    # ...

    return merged_df
```

### 3.3 资金流向因子 (Task 2.3)

**文件**：`src/ashare_lab/features/money_flow.py`

```python
class NorthboundFlowFactor(BaseFeature):
    """
    北向资金流向因子

    计算: 北向净流入 / 市场成交额
    """

    def __init__(self, lookback: int = 5):
        self.lookback = lookback

    @property
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            name=f"northbound_flow_{self.lookback}d",
            normalization=NormalizationMethod.ZSCORE,
        )

    def compute_raw(self, data: dict[str, pd.DataFrame]) -> pd.Series:
        northbound = data["northbound"]  # 北向资金数据
        ohlcv = data["ohlcv"]

        # 北向净流入占比
        flow_ratio = northbound["total_net"] / ohlcv["amount"]

        # N日滚动均值
        return flow_ratio.rolling(self.lookback).mean()


class InstitutionFlowFactor(BaseFeature):
    """
    龙虎榜机构席位因子

    信号: 机构净买入 = 买入额 - 卖出额
    """
    pass  # TODO: 实现
```

### 3.4 GP 因子框架 (Task 2.4)

**目录结构**：
```
src/ashare_lab/features/gp_mining/
├── __init__.py
├── generator.py      # 因子生成器
├── operators.py      # 算子定义
├── evaluator.py      # 因子评估
└── storage.py        # 因子存储
```

**核心设计**：`features/gp_mining/operators.py`

```python
"""
GP 因子挖掘算子库
"""
import numpy as np
import pandas as pd

# 基础算子
def add(x, y): return x + y
def sub(x, y): return x - y
def mul(x, y): return x * y
def div(x, y): return np.where(y != 0, x / y, 0)

# 数学算子
def log(x): return np.log(np.abs(x) + 1e-8)
def sqrt(x): return np.sqrt(np.abs(x))
def sign(x): return np.sign(x)

# 时序算子
def delay(x, d): return pd.Series(x).shift(d).values
def ts_mean(x, d): return pd.Series(x).rolling(d).mean().values
def ts_std(x, d): return pd.Series(x).rolling(d).std().values
def ts_max(x, d): return pd.Series(x).rolling(d).max().values
def ts_min(x, d): return pd.Series(x).rolling(d).min().values

# 截面算子
def rank(x): return pd.Series(x).rank(pct=True).values
def zscore(x): return (x - np.mean(x)) / (np.std(x) + 1e-8)

# 算子注册表
OPERATORS = {
    # 二元算子
    "add": (add, 2),
    "sub": (sub, 2),
    "mul": (mul, 2),
    "div": (div, 2),
    # 一元算子
    "log": (log, 1),
    "sqrt": (sqrt, 1),
    "sign": (sign, 1),
    "rank": (rank, 1),
    "zscore": (zscore, 1),
    # 时序算子 (一元 + 参数)
    "delay": (delay, 1),
    "ts_mean": (ts_mean, 1),
    "ts_std": (ts_std, 1),
}
```

### 3.5 GP 因子挖掘 (Task 2.5)

**文件**：`features/gp_mining/generator.py`

```python
from deap import base, creator, tools, gp, algorithms
import numpy as np

class GPFactorGenerator:
    """
    使用遗传规划自动挖掘因子

    输入: OHLCV + VWAP
    输出: 高IC因子公式
    """

    def __init__(
        self,
        population_size: int = 100,
        generations: int = 50,
        mutation_prob: float = 0.2,
        crossover_prob: float = 0.5,
    ):
        self.pop_size = population_size
        self.generations = generations
        self.mutation_prob = mutation_prob
        self.crossover_prob = crossover_prob

        self._setup_primitives()

    def _setup_primitives(self):
        """配置遗传规划原语"""
        self.pset = gp.PrimitiveSet("MAIN", 6)  # 6个输入: O,H,L,C,V,A

        # 添加算子
        self.pset.addPrimitive(add, 2)
        self.pset.addPrimitive(sub, 2)
        self.pset.addPrimitive(mul, 2)
        self.pset.addPrimitive(div, 2)
        self.pset.addPrimitive(log, 1)
        self.pset.addPrimitive(sqrt, 1)
        self.pset.addPrimitive(rank, 1)

        # 重命名输入
        self.pset.renameArguments(
            ARG0="open", ARG1="high", ARG2="low",
            ARG3="close", ARG4="volume", ARG5="amount"
        )

    def evolve(
        self,
        train_data: pd.DataFrame,
        labels: pd.Series,
        verbose: bool = True,
    ) -> list[dict]:
        """
        运行进化算法

        Returns:
            [{"formula": str, "ic": float, "func": callable}, ...]
        """
        # 定义适应度函数
        def evaluate(individual):
            func = gp.compile(individual, self.pset)
            try:
                factor_values = func(
                    train_data["open"].values,
                    train_data["high"].values,
                    train_data["low"].values,
                    train_data["close"].values,
                    train_data["volume"].values,
                    train_data["amount"].values,
                )
                ic = np.corrcoef(factor_values, labels.values)[0, 1]
                return (abs(ic),) if not np.isnan(ic) else (0,)
            except:
                return (0,)

        # 运行进化
        # ... (DEAP 标准流程)

        return best_factors
```

### 3.6 因子评估工具 (Task 2.6)

**文件**：`src/ashare_lab/evaluation/factor_analysis.py`

```python
def analyze_factor(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    name: str = "factor",
) -> dict:
    """
    分析单个因子的有效性

    Returns:
        {
            "name": str,
            "ic_mean": float,
            "ic_std": float,
            "ir": float,  # IC / IC_std
            "rank_ic_mean": float,
            "turnover": float,  # 因子换手率
            "coverage": float,  # 非NaN比例
        }
    """
    # 按日期分组计算 IC
    daily_ic = factor_values.groupby(level="date").apply(
        lambda x: x.corr(forward_returns.loc[x.index], method="spearman")
    )

    return {
        "name": name,
        "ic_mean": daily_ic.mean(),
        "ic_std": daily_ic.std(),
        "ir": daily_ic.mean() / (daily_ic.std() + 1e-8),
        "rank_ic_mean": daily_ic.mean(),  # spearman 即 rank ic
        "coverage": 1 - factor_values.isna().mean(),
    }
```

---

## 4. 验收标准

### 4.1 功能验收

- [ ] APM 因子正确计算，无未来信息泄露
- [ ] 北向资金数据正常获取和缓存
- [ ] GP 因子框架可运行，生成有效因子公式
- [ ] 因子评估工具输出正确

### 4.2 性能验收

| 因子 | IC 目标 | IR 目标 |
|------|--------|--------|
| APM | > 0.03 | > 0.3 |
| 北向资金 | > 0.02 | > 0.2 |
| GP 最优因子 | > 0.04 | > 0.4 |

---

## 5. 依赖与风险

### 依赖

- AkShare 北向资金接口
- DEAP 遗传规划库

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| AkShare 接口不稳定 | 中 | 多源备份，本地缓存 |
| GP 挖掘计算量大 | 高 | 离线预计算，限制种群大小 |
| 因子过拟合 | 中 | 样本外验证，正则化 |

---

## 6. 后续步骤

完成 Phase 2 后：
1. 将新因子集成到特征融合层
2. 重新训练模型，评估因子贡献度
3. 进入 Phase 3（情绪因子）
