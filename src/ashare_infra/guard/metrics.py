"""量化评估指标

包括IC、RankIC、Sharpe Ratio等常用量化指标。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_pearsonr(x: np.ndarray, y: np.ndarray) -> float:
    """计算 Pearson 相关系数（无 SciPy 依赖）"""
    if x.size < 2 or y.size < 2:
        return 0.0
    x = x.astype(float, copy=False)
    y = y.astype(float, copy=False)
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    corr = np.corrcoef(x, y)[0, 1]
    return 0.0 if np.isnan(corr) else float(corr)


def _safe_spearmanr(x: np.ndarray, y: np.ndarray) -> float:
    """计算 Spearman 相关系数（无 SciPy 依赖，处理 ties）"""
    if x.size < 2 or y.size < 2:
        return 0.0
    x_rank = pd.Series(x).rank(method="average").to_numpy()
    y_rank = pd.Series(y).rank(method="average").to_numpy()
    return _safe_pearsonr(x_rank, y_rank)


def information_coefficient(predictions: np.ndarray, labels: np.ndarray) -> float:
    """计算信息系数（IC）

    IC是预测值与真实值之间的Pearson相关系数，衡量预测的线性相关性。

    Args:
        predictions: 预测值数组
        labels: 真实标签数组

    Returns:
        IC值（-1到1之间）
    """
    if len(predictions) == 0 or len(labels) == 0:
        return 0.0

    # 移除NaN值
    mask = ~(np.isnan(predictions) | np.isnan(labels))
    if mask.sum() < 2:
        return 0.0

    predictions_clean = predictions[mask]
    labels_clean = labels[mask]

    return _safe_pearsonr(predictions_clean, labels_clean)


def rank_information_coefficient(predictions: np.ndarray, labels: np.ndarray) -> float:
    """计算秩信息系数（RankIC）

    RankIC是预测值排序与真实值排序之间的Spearman相关系数，
    更关注相对排序而非绝对值，对异常值更鲁棒。

    Args:
        predictions: 预测值数组
        labels: 真实标签数组

    Returns:
        RankIC值（-1到1之间）
    """
    if len(predictions) == 0 or len(labels) == 0:
        return 0.0

    # 移除NaN值
    mask = ~(np.isnan(predictions) | np.isnan(labels))
    if mask.sum() < 2:
        return 0.0

    predictions_clean = predictions[mask]
    labels_clean = labels[mask]

    return _safe_spearmanr(predictions_clean, labels_clean)


def mean_squared_error(predictions: np.ndarray, labels: np.ndarray) -> float:
    """计算均方误差（MSE）

    Args:
        predictions: 预测值数组
        labels: 真实标签数组

    Returns:
        MSE值
    """
    if len(predictions) == 0 or len(labels) == 0:
        return float("inf")

    # 移除NaN值
    mask = ~(np.isnan(predictions) | np.isnan(labels))
    if mask.sum() == 0:
        return float("inf")

    predictions_clean = predictions[mask]
    labels_clean = labels[mask]

    mse = np.mean((predictions_clean - labels_clean) ** 2)
    return float(mse)


def mean_absolute_error(predictions: np.ndarray, labels: np.ndarray) -> float:
    """计算平均绝对误差（MAE）

    Args:
        predictions: 预测值数组
        labels: 真实标签数组

    Returns:
        MAE值
    """
    if len(predictions) == 0 or len(labels) == 0:
        return float("inf")

    # 移除NaN值
    mask = ~(np.isnan(predictions) | np.isnan(labels))
    if mask.sum() == 0:
        return float("inf")

    predictions_clean = predictions[mask]
    labels_clean = labels[mask]

    mae = np.mean(np.abs(predictions_clean - labels_clean))
    return float(mae)


def sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    """计算Sharpe比率

    Sharpe比率 = (平均收益 - 无风险收益) / 收益标准差

    Args:
        returns: 收益率数组
        risk_free_rate: 无风险收益率（默认0）

    Returns:
        Sharpe比率
    """
    if len(returns) == 0:
        return 0.0

    # 移除NaN值
    returns_clean = returns[~np.isnan(returns)]
    if len(returns_clean) < 2:
        return 0.0

    mean_return = np.mean(returns_clean)
    std_return = np.std(returns_clean, ddof=1)

    if std_return == 0:
        return 0.0

    sharpe = (mean_return - risk_free_rate) / std_return
    return float(sharpe)


def calculate_daily_ic(
    predictions: pd.DataFrame,
    labels: pd.DataFrame,
    date_col: str = "date",
) -> pd.DataFrame:
    """计算每日IC和RankIC

    Args:
        predictions: 包含预测值的DataFrame（必须有date_col和预测值列）
        labels: 包含真实标签的DataFrame（必须有date_col和标签列）
        date_col: 日期列名

    Returns:
        每日IC和RankIC的DataFrame
    """
    # 合并预测和标签
    merged = pd.merge(
        predictions,
        labels,
        on=[date_col, "symbol"],
        suffixes=("_pred", "_true"),
    )

    # 按日期分组计算IC
    daily_metrics = []

    for date, group in merged.groupby(date_col):
        preds = group["label_pred"].values
        labels = group["label_true"].values

        ic = information_coefficient(preds, labels)
        rank_ic = rank_information_coefficient(preds, labels)

        daily_metrics.append(
            {
                date_col: date,
                "ic": ic,
                "rank_ic": rank_ic,
                "n_samples": len(group),
            }
        )

    return pd.DataFrame(daily_metrics)


def calculate_daily_cs_ic(
    predictions: pd.Series,
    labels: pd.Series,
    method: str = "pearson",
) -> pd.Series:
    """逐日计算横截面 IC（Cross-Sectional IC）

    每个交易日内，计算所有股票的预测值与真实值之间的相关系数。
    这是评估因子/模型预测能力的核心指标。

    Args:
        predictions: 预测值 Series，索引为 (date, symbol) 的 MultiIndex
        labels: 真实标签 Series，索引为 (date, symbol) 的 MultiIndex
        method: 相关系数计算方法，"pearson" 或 "spearman"

    Returns:
        每日 IC 的 Series，索引为 date

    示例:
        >>> preds = pd.Series([0.1, 0.2, -0.1], index=pd.MultiIndex.from_tuples([
        ...     ('2024-01-01', 'A'), ('2024-01-01', 'B'), ('2024-01-01', 'C')
        ... ], names=['date', 'symbol']))
        >>> labels = pd.Series([0.15, 0.18, -0.08], index=preds.index)
        >>> daily_ic = calculate_daily_cs_ic(preds, labels)
    """
    if not isinstance(predictions.index, pd.MultiIndex):
        raise ValueError("predictions 必须有 (date, symbol) 的 MultiIndex")
    if not isinstance(labels.index, pd.MultiIndex):
        raise ValueError("labels 必须有 (date, symbol) 的 MultiIndex")

    # 确保索引名称正确
    if predictions.index.names[0] not in ("date", "Date"):
        raise ValueError(f"第一层索引应为 'date'，实际为 {predictions.index.names[0]}")

    # 对齐数据（只保留两者都有的 (date, symbol) 组合）
    aligned_preds, aligned_labels = predictions.align(labels, join="inner")

    if len(aligned_preds) == 0:
        return pd.Series(dtype=float, name="ic")

    # 按日期分组
    date_level = 0  # 第一层是 date
    grouped_preds = aligned_preds.groupby(level=date_level)
    grouped_labels = aligned_labels.groupby(level=date_level)

    daily_ic_list = []
    for date in sorted(aligned_preds.index.get_level_values(date_level).unique()):
        try:
            pred_day = grouped_preds.get_group(date).values
            label_day = grouped_labels.get_group(date).values

            if method == "pearson":
                ic = information_coefficient(pred_day, label_day)
            elif method == "spearman":
                ic = rank_information_coefficient(pred_day, label_day)
            else:
                raise ValueError(f"不支持的 method: {method}，仅支持 'pearson' 或 'spearman'")

            daily_ic_list.append({"date": date, "ic": ic})
        except KeyError:
            # 该日期在某个 Series 中不存在，跳过
            continue

    if not daily_ic_list:
        return pd.Series(dtype=float, name="ic")

    daily_ic_df = pd.DataFrame(daily_ic_list)
    return daily_ic_df.set_index("date")["ic"]


def summarize_daily_cs(daily_ic: pd.Series) -> dict[str, float]:
    """汇总 Daily-CS IC 统计指标

    Args:
        daily_ic: 每日 IC 的 Series（索引为 date）

    Returns:
        统计指标字典，包含：
        - mean_ic: 平均 IC
        - std_ic: IC 标准差
        - icir: IC 信息比率（mean_ic / std_ic），衡量稳定性
        - t_stat: t 统计量（检验 IC 是否显著不为 0）
        - n_days: 有效交易日数量

    示例:
        >>> daily_ic = pd.Series([0.05, 0.03, 0.08, -0.02, 0.06])
        >>> stats = summarize_daily_cs(daily_ic)
        >>> print(stats['icir'])  # IC 信息比率
    """
    # 移除 NaN 值
    valid_ic = daily_ic.dropna()

    if len(valid_ic) == 0:
        return {
            "mean_ic": 0.0,
            "std_ic": 0.0,
            "icir": 0.0,
            "t_stat": 0.0,
            "n_days": 0,
        }

    mean_ic = float(valid_ic.mean())
    std_ic = float(valid_ic.std(ddof=1)) if len(valid_ic) > 1 else 0.0

    # ICIR: IC 信息比率，衡量 IC 的稳定性
    icir = mean_ic / std_ic if std_ic > 0 else 0.0

    # t 统计量：检验 IC 是否显著不为 0
    # t = mean / (std / sqrt(n))
    n = len(valid_ic)
    t_stat = mean_ic / (std_ic / np.sqrt(n)) if std_ic > 0 and n > 0 else 0.0

    return {
        "mean_ic": mean_ic,
        "std_ic": std_ic,
        "icir": float(icir),
        "t_stat": float(t_stat),
        "n_days": int(n),
    }


def aggregate_daily_to_monthly(daily_ic: pd.Series) -> pd.DataFrame:
    """将 Daily-CS IC 按月汇总

    Args:
        daily_ic: 每日 IC 的 Series（索引为 date）

    Returns:
        月度汇总的 DataFrame，列包含：
        - year_month: 年月字符串（YYYY-MM）
        - mean_ic: 该月平均 IC
        - std_ic: 该月 IC 标准差
        - n_days: 该月有效交易日数量

    示例:
        >>> daily_ic = pd.Series([0.05, 0.03, 0.08],
        ...     index=pd.to_datetime(['2024-01-02', '2024-01-03', '2024-02-01']))
        >>> monthly = aggregate_daily_to_monthly(daily_ic)
    """
    if daily_ic.empty:
        return pd.DataFrame(columns=["year_month", "mean_ic", "std_ic", "n_days"])

    # 确保索引是 datetime 类型
    if not isinstance(daily_ic.index, pd.DatetimeIndex):
        daily_ic.index = pd.to_datetime(daily_ic.index)

    # 移除 NaN 值
    valid_ic = daily_ic.dropna()

    if valid_ic.empty:
        return pd.DataFrame(columns=["year_month", "mean_ic", "std_ic", "n_days"])

    # 按年月分组
    monthly_groups = valid_ic.groupby(valid_ic.index.to_period("M"))

    monthly_stats = []
    for period, group in monthly_groups:
        mean_ic = float(group.mean())
        std_ic = float(group.std(ddof=1)) if len(group) > 1 else 0.0
        n_days = len(group)

        monthly_stats.append({
            "year_month": str(period),  # 格式如 "2024-01"
            "mean_ic": mean_ic,
            "std_ic": std_ic,
            "n_days": n_days,
        })

    return pd.DataFrame(monthly_stats)


def evaluate_model(predictions: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """综合评估模型性能

    Args:
        predictions: 预测值数组
        labels: 真实标签数组

    Returns:
        包含各项指标的字典
    """
    metrics = {
        "mse": mean_squared_error(predictions, labels),
        "mae": mean_absolute_error(predictions, labels),
        "ic": information_coefficient(predictions, labels),
        "rank_ic": rank_information_coefficient(predictions, labels),
    }

    return metrics
