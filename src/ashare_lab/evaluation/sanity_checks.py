"""防伪门禁 Sanity Check

提供三种标准化的信号有效性检验：
1. Shuffle Labels - 打乱预测排序，IC 应归零
2. Time Reverse - 时间反转，IC 应归零
3. Lag-1 - 信号延迟一天，IC 应显著下降
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_lab.evaluation.metrics import calculate_daily_cs_ic, summarize_daily_cs


def _validate_multi_index(series: pd.Series, name: str) -> None:
    """验证 Series 具有 (date, symbol) MultiIndex"""
    if not isinstance(series.index, pd.MultiIndex):
        raise ValueError(f"{name} 必须有 (date, symbol) 的 MultiIndex")


def compute_baseline_ic(
    predictions: pd.Series,
    labels: pd.Series,
    method: str = "pearson",
) -> dict[str, float]:
    """计算基线 Daily-CS IC 统计

    Args:
        predictions: 预测值，索引为 (date, symbol)
        labels: 真实标签，索引为 (date, symbol)
        method: 相关系数方法

    Returns:
        汇总统计字典 {mean_ic, std_ic, icir, t_stat, n_days}
    """
    _validate_multi_index(predictions, "predictions")
    _validate_multi_index(labels, "labels")
    daily_ic = calculate_daily_cs_ic(predictions, labels, method=method)
    return summarize_daily_cs(daily_ic)


def shuffle_test(
    predictions: pd.Series,
    labels: pd.Series,
    method: str = "pearson",
    n_trials: int = 5,
    threshold: float = 0.02,
    seed: int = 42,
) -> dict:
    """Shuffle Labels 检验

    在每个日期内随机打乱预测排序，重复 n_trials 次取平均 IC。
    如果模型有真正的预测能力，打乱后 IC 应接近 0。

    Args:
        predictions: 预测值，索引为 (date, symbol)
        labels: 真实标签，索引为 (date, symbol)
        method: 相关系数方法
        n_trials: 重复实验次数
        threshold: |mean_ic| < threshold 视为通过
        seed: 随机种子

    Returns:
        {mean_ic, pass, threshold, n_trials}
    """
    _validate_multi_index(predictions, "predictions")
    _validate_multi_index(labels, "labels")

    shuffled_ics: list[float] = []
    for trial in range(n_trials):
        rng = np.random.RandomState(seed + trial)
        shuffled = predictions.copy()

        # 按日期分组打乱（保持每日股票池不变，只打乱排序）
        dates = shuffled.index.get_level_values(0).unique()
        for date in dates:
            mask = shuffled.index.get_level_values(0) == date
            vals = shuffled.loc[mask].values.copy()
            rng.shuffle(vals)
            shuffled.loc[mask] = vals

        daily_ic = calculate_daily_cs_ic(shuffled, labels, method=method)
        stats = summarize_daily_cs(daily_ic)
        shuffled_ics.append(stats["mean_ic"])

    avg_ic = float(np.mean(shuffled_ics))
    return {
        "mean_ic": avg_ic,
        "pass": bool(abs(avg_ic) < threshold),
        "threshold": threshold,
        "n_trials": n_trials,
    }


def time_reverse_test(
    predictions: pd.Series,
    labels: pd.Series,
    method: str = "pearson",
    threshold: float = 0.02,
) -> dict:
    """Time Reverse 检验

    将预测信号的日期顺序反转（第一天的预测匹配最后一天的标签），
    如果模型捕捉到了真正的因果信号，时间反转后应该失效。

    Args:
        predictions: 预测值，索引为 (date, symbol)
        labels: 真实标签，索引为 (date, symbol)
        method: 相关系数方法
        threshold: |mean_ic| < threshold 视为通过

    Returns:
        {mean_ic, pass, threshold}
    """
    _validate_multi_index(predictions, "predictions")
    _validate_multi_index(labels, "labels")

    dates = sorted(predictions.index.get_level_values(0).unique())
    if len(dates) < 2:
        return {
            "mean_ic": 0.0,
            "pass": True,
            "threshold": threshold,
            "error": "dates < 2, skipped",
        }

    reversed_dates = list(reversed(dates))
    date_map = dict(zip(dates, reversed_dates))

    # 重建预测序列，日期映射到反转后的日期
    new_tuples = []
    new_values = []
    for (date, symbol), value in predictions.items():
        new_tuples.append((date_map[date], symbol))
        new_values.append(value)

    reversed_preds = pd.Series(
        new_values,
        index=pd.MultiIndex.from_tuples(new_tuples, names=predictions.index.names),
    )
    reversed_preds = reversed_preds.sort_index()

    daily_ic = calculate_daily_cs_ic(reversed_preds, labels, method=method)
    stats = summarize_daily_cs(daily_ic)

    return {
        "mean_ic": stats["mean_ic"],
        "pass": bool(abs(stats["mean_ic"]) < threshold),
        "threshold": threshold,
    }


def lag1_test(
    predictions: pd.Series,
    labels: pd.Series,
    baseline_mean_ic: float,
    method: str = "pearson",
    threshold: float = 0.01,
) -> dict:
    """Lag-1 检验

    将预测信号延迟一个交易日（用 t-1 的预测匹配 t 的标签），
    如果模型信号有真实的时效性，延迟后 IC 应显著下降。

    Args:
        predictions: 预测值，索引为 (date, symbol)
        labels: 真实标签，索引为 (date, symbol)
        baseline_mean_ic: 基线 mean_ic（用于计算 IC 下降幅度）
        method: 相关系数方法
        threshold: IC 下降幅度 > threshold 视为通过

    Returns:
        {baseline_mean_ic, lag1_mean_ic, ic_drop, pass, threshold}
    """
    _validate_multi_index(predictions, "predictions")
    _validate_multi_index(labels, "labels")

    dates = sorted(predictions.index.get_level_values(0).unique())
    if len(dates) < 2:
        return {
            "baseline_mean_ic": baseline_mean_ic,
            "lag1_mean_ic": 0.0,
            "ic_drop": 0.0,
            "pass": False,
            "threshold": threshold,
            "error": "dates < 2, skipped",
        }

    # 日期映射：dates[i] 的预测 -> dates[i+1] 的标签
    date_map = dict(zip(dates[:-1], dates[1:]))

    lagged_tuples = []
    lagged_values = []
    for (date, symbol), value in predictions.items():
        if date in date_map:
            lagged_tuples.append((date_map[date], symbol))
            lagged_values.append(value)

    if not lagged_tuples:
        return {
            "baseline_mean_ic": baseline_mean_ic,
            "lag1_mean_ic": 0.0,
            "ic_drop": 0.0,
            "pass": False,
            "threshold": threshold,
            "error": "no valid lagged data",
        }

    lagged_preds = pd.Series(
        lagged_values,
        index=pd.MultiIndex.from_tuples(lagged_tuples, names=predictions.index.names),
    )
    lagged_preds = lagged_preds.sort_index()

    daily_ic = calculate_daily_cs_ic(lagged_preds, labels, method=method)
    stats = summarize_daily_cs(daily_ic)

    lag1_mean_ic = stats["mean_ic"]
    ic_drop = baseline_mean_ic - lag1_mean_ic

    return {
        "baseline_mean_ic": baseline_mean_ic,
        "lag1_mean_ic": lag1_mean_ic,
        "ic_drop": float(ic_drop),
        "pass": bool(ic_drop > threshold),
        "threshold": threshold,
    }


def run_all_checks(
    predictions: pd.Series,
    labels: pd.Series,
    method: str = "pearson",
    shuffle_n_trials: int = 5,
    shuffle_threshold: float = 0.02,
    reverse_threshold: float = 0.02,
    lag1_threshold: float = 0.01,
    seed: int = 42,
) -> dict:
    """运行全部三项 Sanity Check

    Args:
        predictions: 预测值，索引为 (date, symbol)
        labels: 真实标签，索引为 (date, symbol)
        method: 相关系数方法
        shuffle_n_trials: Shuffle 实验重复次数
        shuffle_threshold: Shuffle 检验阈值
        reverse_threshold: Time Reverse 检验阈值
        lag1_threshold: Lag-1 IC 下降阈值
        seed: 随机种子

    Returns:
        包含 baseline, shuffle_labels, time_reverse, lag_1 四个子字典的结果
    """
    baseline = compute_baseline_ic(predictions, labels, method=method)

    result = {
        "baseline": baseline,
        "shuffle_labels": shuffle_test(
            predictions, labels,
            method=method,
            n_trials=shuffle_n_trials,
            threshold=shuffle_threshold,
            seed=seed,
        ),
        "time_reverse": time_reverse_test(
            predictions, labels,
            method=method,
            threshold=reverse_threshold,
        ),
        "lag_1": lag1_test(
            predictions, labels,
            baseline_mean_ic=baseline["mean_ic"],
            method=method,
            threshold=lag1_threshold,
        ),
    }

    # 汇总通过状态
    result["all_pass"] = all(
        result[k].get("pass", False)
        for k in ["shuffle_labels", "time_reverse", "lag_1"]
    )

    return result
