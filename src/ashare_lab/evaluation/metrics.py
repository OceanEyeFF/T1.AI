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
