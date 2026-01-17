# Phase 2: 验证与评估

**预计工作量：** 2天
**优先级：** ⭐⭐ 中高
**目标：** 验证推荐系统准确性，建立历史推荐管理机制

---

## 任务概览

| 任务ID | 任务名称 | 预计时间 | 依赖 | 状态 |
|--------|---------|---------|------|------|
| 2.1 | 推荐验证器 | 1天 | Phase 1 | 🔲 待开始 |
| 2.2 | 历史推荐管理 | 0.5天 | 2.1 | 🔲 待开始 |
| 2.3 | 评估脚本与报告 | 0.5天 | 2.1, 2.2 | 🔲 待开始 |

---

## 任务2.1：推荐验证器 ⭐⭐⭐

**目标：** 实现RecommendationValidator，验证前一日推荐的准确性

### 交付物

- `src/ashare_lab/recommendation/validator.py` - RecommendationValidator类
- `scripts/validate_recommendations.py` - 验证脚本
- `tests/test_recommendation_validator.py` - 单元测试

### 详细任务

#### 2.1.1 实现 RecommendationValidator 类

**代码位置：** `src/ashare_lab/recommendation/validator.py`

**核心功能：**
```python
from dataclasses import dataclass
from typing import List
import pandas as pd

@dataclass
class ValidationResult:
    date: str                    # 推荐日期
    horizon: str                 # 时间跨度（3d/5d/10d）
    hit_rate: float              # 命中率（上涨股票占比）
    avg_return: float            # Top-N平均收益
    ic: float                    # 信息系数（预测值vs实际值）
    rank_ic: float               # 排名IC
    top_n_cumulative_return: float  # Top-N累计收益
    benchmark_return: float      # 基准收益（沪深300）
    excess_return: float         # 超额收益

class RecommendationValidator:
    def __init__(self, data_source):
        self.data_source = data_source

    def validate_recommendations(
        self,
        recommendations: dict[str, List[Recommendation]],
        recommendation_date: str,
    ) -> dict[str, ValidationResult]:
        """
        验证推荐准确性

        Args:
            recommendations: {
                "3d": [Top 10],
                "5d": [Top 10],
                "10d": [Top 10],
            }
            recommendation_date: 推荐日期（YYYYMMDD）

        Returns:
            {
                "3d": ValidationResult,
                "5d": ValidationResult,
                "10d": ValidationResult,
            }
        """
        results = {}

        for horizon, recs in recommendations.items():
            # 计算实际持有期（从推荐日+1开始）
            horizon_days = int(horizon[:-1])  # "3d" -> 3
            start_date = get_next_trading_day(recommendation_date)
            end_date = get_nth_trading_day(start_date, horizon_days)

            # 获取实际收益
            actual_returns = self._get_actual_returns(
                [rec.symbol for rec in recs],
                start_date,
                end_date,
            )

            # 计算验证指标
            result = self._compute_metrics(
                recs, actual_returns, horizon, recommendation_date
            )
            results[horizon] = result

        return results

    def _get_actual_returns(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.Series:
        """获取实际收益率"""
        returns = {}
        for symbol in symbols:
            data = self.data_source.fetch(symbol, start_date, end_date)
            if len(data) >= 2:
                ret = data.iloc[-1]["close"] / data.iloc[0]["close"] - 1
                returns[symbol] = ret
            else:
                returns[symbol] = np.nan  # 停牌/缺价
        return pd.Series(returns)

    def _compute_metrics(
        self,
        recommendations: List[Recommendation],
        actual_returns: pd.Series,
        horizon: str,
        date: str,
    ) -> ValidationResult:
        """计算验证指标"""
        # 命中率：上涨股票占比
        hit_rate = (actual_returns > 0).sum() / len(actual_returns)

        # Top-N平均收益
        avg_return = actual_returns.mean()

        # IC：预测收益 vs 实际收益的相关性
        predicted_returns = pd.Series({
            rec.symbol: rec.predicted_return for rec in recommendations
        })
        ic = predicted_returns.corr(actual_returns)

        # Rank IC：预测排名 vs 实际排名的相关性
        pred_ranks = predicted_returns.rank(ascending=False)
        actual_ranks = actual_returns.rank(ascending=False)
        rank_ic = pred_ranks.corr(actual_ranks, method="spearman")

        # Top-N累计收益
        cumulative_return = (1 + actual_returns).prod() - 1

        # 基准收益（沪深300）
        benchmark_return = self._get_benchmark_return(date, horizon)

        # 超额收益
        excess_return = avg_return - benchmark_return

        return ValidationResult(
            date=date,
            horizon=horizon,
            hit_rate=hit_rate,
            avg_return=avg_return,
            ic=ic,
            rank_ic=rank_ic,
            top_n_cumulative_return=cumulative_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
        )
```

#### 2.1.2 创建验证脚本

**代码位置：** `scripts/validate_recommendations.py`

**功能：**
```python
from ashare_lab.recommendation.validator import RecommendationValidator
import json

def main(recommendation_file: str, recommendation_date: str):
    # Step 1: 加载推荐结果
    with open(recommendation_file) as f:
        recommendations = json.load(f)

    # Step 2: 验证推荐
    validator = RecommendationValidator(data_source)
    results = validator.validate_recommendations(
        recommendations, recommendation_date
    )

    # Step 3: 打印验证结果
    for horizon, result in results.items():
        print(f"\n{'='*50}")
        print(f"{horizon.upper()} 验证结果")
        print(f"{'='*50}")
        print(f"命中率: {result.hit_rate:.1%}")
        print(f"平均收益: {result.avg_return:.2%}")
        print(f"IC: {result.ic:.4f}")
        print(f"Rank IC: {result.rank_ic:.4f}")
        print(f"Top-10累计收益: {result.top_n_cumulative_return:.2%}")
        print(f"基准收益: {result.benchmark_return:.2%}")
        print(f"超额收益: {result.excess_return:.2%}")

    # Step 4: 保存验证报告
    save_validation_report(results, f"output/validations/{recommendation_date}.json")

if __name__ == "__main__":
    main(
        recommendation_file="output/recommendations/20250115.json",
        recommendation_date="20250115"
    )
```

#### 2.1.3 编写单元测试

**代码位置：** `tests/test_recommendation_validator.py`

**测试用例：**
- ✅ 命中率计算正确性
- ✅ IC/Rank IC计算正确性
- ✅ 超额收益计算正确性
- ✅ 停牌股票处理（NaN掩码）

**验收标准：**
- ✅ 所有测试通过
- ✅ 验证指标数值合理（IC范围[-1, 1]，命中率范围[0, 1]）

---

## 任务2.2：历史推荐管理 ⭐⭐

**目标：** 实现RecommendationHistory，持久化推荐记录并提供查询接口

### 交付物

- `src/ashare_lab/recommendation/history.py` - RecommendationHistory类
- 推荐历史数据库（SQLite或Parquet）

### 详细任务

#### 2.2.1 实现 RecommendationHistory 类

**代码位置：** `src/ashare_lab/recommendation/history.py`

**核心功能：**
```python
from pathlib import Path
import sqlite3
import pandas as pd

class RecommendationHistory:
    def __init__(self, db_path: str = "data/recommendation_history.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                horizon TEXT NOT NULL,
                rank INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                predicted_return REAL,
                confidence REAL,
                reason TEXT,
                actual_return REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                horizon TEXT NOT NULL,
                hit_rate REAL,
                avg_return REAL,
                ic REAL,
                rank_ic REAL,
                cumulative_return REAL,
                benchmark_return REAL,
                excess_return REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save_recommendations(
        self,
        date: str,
        recommendations: dict[str, List[Recommendation]],
    ):
        """保存推荐记录"""
        conn = sqlite3.connect(self.db_path)
        for horizon, recs in recommendations.items():
            for rec in recs:
                conn.execute("""
                    INSERT INTO recommendations
                    (date, horizon, rank, symbol, name, predicted_return, confidence, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (date, horizon, rec.rank, rec.symbol, rec.name,
                      rec.predicted_return, rec.confidence, rec.reason))
        conn.commit()
        conn.close()

    def save_validation_results(
        self,
        date: str,
        results: dict[str, ValidationResult],
    ):
        """保存验证结果"""
        conn = sqlite3.connect(self.db_path)
        for horizon, result in results.items():
            conn.execute("""
                INSERT INTO validations
                (date, horizon, hit_rate, avg_return, ic, rank_ic,
                 cumulative_return, benchmark_return, excess_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, horizon, result.hit_rate, result.avg_return,
                  result.ic, result.rank_ic, result.top_n_cumulative_return,
                  result.benchmark_return, result.excess_return))
        conn.commit()
        conn.close()

    def query_recommendations(
        self,
        start_date: str,
        end_date: str,
        horizon: str = None,
    ) -> pd.DataFrame:
        """查询推荐历史"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM recommendations WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]

        if horizon:
            query += " AND horizon = ?"
            params.append(horizon)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_monthly_stats(self, year_month: str) -> pd.DataFrame:
        """获取月度统计"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT
                horizon,
                COUNT(DISTINCT date) as recommendation_days,
                AVG(hit_rate) as avg_hit_rate,
                AVG(avg_return) as avg_return,
                AVG(ic) as avg_ic,
                AVG(rank_ic) as avg_rank_ic,
                AVG(excess_return) as avg_excess_return
            FROM validations
            WHERE date LIKE ?
            GROUP BY horizon
        """
        df = pd.read_sql_query(query, conn, params=[f"{year_month}%"])
        conn.close()
        return df
```

**验收标准：**
- ✅ 成功保存推荐记录和验证结果
- ✅ 查询功能正常（按日期/时间跨度过滤）
- ✅ 月度统计准确

---

## 任务2.3：评估脚本与报告 ⭐⭐

**目标：** 创建评估脚本，生成月度统计报告

### 交付物

- `scripts/evaluate_recommendation.py` - 评估脚本
- 月度统计报告（Markdown格式）

### 详细任务

#### 2.3.1 创建评估脚本

**代码位置：** `scripts/evaluate_recommendation.py`

**功能：**
```python
from ashare_lab.recommendation.history import RecommendationHistory

def main(year_month: str):
    # Step 1: 获取月度统计
    history = RecommendationHistory()
    stats = history.get_monthly_stats(year_month)

    # Step 2: 生成Markdown报告
    with open(f"output/reports/{year_month}_report.md", "w") as f:
        f.write(f"# {year_month} 推荐系统月度报告\n\n")

        for _, row in stats.iterrows():
            horizon = row["horizon"]
            f.write(f"## {horizon.upper()} 推荐\n\n")
            f.write(f"- **推荐天数：** {row['recommendation_days']}\n")
            f.write(f"- **平均命中率：** {row['avg_hit_rate']:.1%}\n")
            f.write(f"- **平均收益：** {row['avg_return']:.2%}\n")
            f.write(f"- **平均IC：** {row['avg_ic']:.4f}\n")
            f.write(f"- **平均Rank IC：** {row['avg_rank_ic']:.4f}\n")
            f.write(f"- **平均超额收益：** {row['avg_excess_return']:.2%}\n\n")

    # Step 3: 打印报告
    print(f"✅ 月度报告已生成：output/reports/{year_month}_report.md")

if __name__ == "__main__":
    main("202501")
```

**验收标准：**
- ✅ 成功生成月度报告
- ✅ 报告内容准确（统计数值合理）

---

## Phase 2 总体验收标准

### 功能验收

- ✅ 推荐验证器正常工作（计算命中率/IC/超额收益）
- ✅ 历史推荐数据成功持久化（SQLite数据库）
- ✅ 查询功能正常（按日期/时间跨度过滤）
- ✅ 月度统计报告生成成功

### 质量验证

- ✅ 验证指标数值合理：
  - IC范围：[-1, 1]
  - 命中率范围：[0, 1]
  - 超额收益合理（不会出现±100%）
- ✅ 所有单元测试通过（新增测试 ≥ 5个）

### 文档验证

- ✅ 更新主设计文档（反映验证功能）
- ✅ 月度报告格式规范、可读性强

---

## 下一步行动

完成Phase 2后，立即进入 **Phase 3: 自动化与生产化**

参见：[phase3_automation.md](./phase3_automation.md)
