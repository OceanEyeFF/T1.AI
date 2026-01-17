#!/usr/bin/env python
"""每日增量Pipeline

包含以下步骤：
1) 增量拉取最新交易日数据（TuShare）
2) 重算近30日特征/标签
3) warm-start 增量训练（可跳过）
4) 生成 Top-10 推荐榜单
5) 评估前一日推荐命中率

支持 ``--dry-run`` 生成可重复的合成数据，方便本地/CI 快速验证。
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict

import numpy as np
import pandas as pd
import torch

from ashare_lab.data.tushare_source import TushareDailyBarsRequest, load_or_fetch_daily_bars
from ashare_lab.models.transformer import create_mtl_model, freeze_encoder_layers

from scripts.evaluate_recommendation import evaluate_top_k, generate_report

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FetchFn = Callable[[TushareDailyBarsRequest, Path], pd.DataFrame]


def _to_timestamp(date_like: str | datetime | pd.Timestamp) -> pd.Timestamp:
    """将输入统一为 pandas Timestamp。"""
    return pd.to_datetime(date_like)


def incremental_update(
    symbols: list[str],
    date: str | datetime | pd.Timestamp,
    cache_dir: Path,
    fetch_fn: FetchFn = load_or_fetch_daily_bars,
) -> dict[str, pd.DataFrame]:
    """仅拉取目标交易日的数据并返回 {symbol: df}。

    Args:
        symbols: 需要更新的股票列表
        date: 交易日（任意可解析日期格式）
        cache_dir: 缓存目录
        fetch_fn: 可注入的拉取函数（便于测试）
    """
    target = _to_timestamp(date)
    date_str = target.strftime("%Y%m%d")
    results: dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        req = TushareDailyBarsRequest(
            symbol=symbol,
            start_date=date_str,
            end_date=date_str,
            adjust="qfq",
        )
        df = fetch_fn(req, cache_dir)
        if df.empty:
            logger.warning("No data fetched for %s on %s", symbol, date_str)
            continue

        # 仅保留目标交易日（防御性过滤）
        filtered = df.loc[df.index == target].copy()
        filtered["symbol"] = symbol
        results[symbol] = filtered

    if not results:
        raise ValueError("No data fetched for any symbol")

    return results


def _synthetic_history(
    end_date: pd.Timestamp,
    symbols: list[str],
    days: int = 40,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """生成可重复的合成行情序列，用于 dry-run/测试。"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end_date - timedelta(days=days - 1), end_date, freq="B")
    history: dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        base = 10 + rng.normal(0, 0.5)
        shocks = rng.normal(0, 0.01, size=len(dates)).cumsum()
        close = base * (1 + shocks)
        df = pd.DataFrame(
            {
                "open": close * (1 + rng.normal(0, 0.001, size=len(dates))),
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": rng.integers(1_000, 5_000, size=len(dates)),
                "amount": rng.integers(100_000, 300_000, size=len(dates)),
            },
            index=dates,
        )
        df.index.name = "date"
        history[symbol] = df
    return history


def recompute_features_labels(
    data_map: dict[str, pd.DataFrame],
    window: int = 30,
) -> pd.DataFrame:
    """以 30 日滚动窗口重算特征与标签。

    - 特征：window 日动量 ``close / close.shift(window) - 1``
    - 标签：次日涨跌幅 ``close.shift(-1) / close - 1``
    """
    frames: list[pd.DataFrame] = []

    for symbol, df in data_map.items():
        df_sorted = df.sort_index()
        close = df_sorted["close"]
        momentum = close / close.shift(window) - 1
        next_return = close.shift(-1) / close - 1

        out = pd.DataFrame(
            {
                "date": df_sorted.index,
                "symbol": symbol,
                "feature_momentum": momentum,
                "label_next": next_return,
                "close": close,
            }
        )
        # 仅保留最近 window 行，窗口不足也照常返回
        frames.append(out.tail(window))

    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "feature_momentum", "label_next", "close"])

    return pd.concat(frames).reset_index(drop=True)


def _latest_checkpoint(save_dir: Path) -> Path | None:
    """找到目录下最新的 checkpoint 文件。"""
    candidates = sorted(save_dir.glob("*.pt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def warm_start_incremental_train(
    checkpoint_dir: Path,
    freeze_layers: int = 0,
    epochs: int = 1,
    dry_run: bool = True,
) -> tuple[torch.nn.Module, Dict[str, Path | None]]:
    """基于最新 checkpoint 进行少量增量训练（可 dry-run）。

    Returns:
        (model, meta) 其中 meta 包含 warm_start 来源与新 checkpoint 路径。
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    model = create_mtl_model(input_dim=6, min_seq_len=30)

    warm = _latest_checkpoint(checkpoint_dir)
    if warm and warm.exists():
        try:
            state = torch.load(warm, map_location="cpu", weights_only=False)
            model.load_state_dict(state["model_state_dict"])
            logger.info("Warm-start from %s", warm)
        except Exception as exc:  # pragma: no cover - 容错分支
            logger.warning("Failed to load checkpoint %s: %s", warm, exc)

    if freeze_layers > 0:
        freeze_encoder_layers(model, freeze_layers)
        logger.info("Frozen first %s encoder layer(s)", freeze_layers)

    # 简化训练：使用合成小批量跑若干步，保证参数可更新
    if not dry_run:
        torch.manual_seed(7)
        features = torch.randn(32, 30, model.config.input_dim)
        labels = torch.randn(32, 3)
        opt = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            _, losses = model(features, labels)
            losses["total"].backward()
            opt.step()

    out_path = checkpoint_dir / f"incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
    torch.save({"model_state_dict": model.state_dict(), "meta": {"freeze_layers": freeze_layers}}, out_path)

    return model, {"checkpoint": out_path, "warm_start": warm}


def _is_st_or_star(symbol: str) -> bool:
    upper = symbol.upper()
    return upper.startswith(("ST", "*ST")) or upper.startswith(("688", "689"))


def generate_recommendations(
    feature_df: pd.DataFrame,
    target_date: pd.Timestamp,
    top_n: int = 10,
    output_dir: Path | None = None,
) -> pd.DataFrame:
    """根据特征动量生成 Top-N 推荐榜单，过滤 ST/科创板。"""
    if feature_df.empty:
        raise ValueError("feature_df is empty")

    df = feature_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    sliced = df[df["date"] == target_date]
    if sliced.empty:
        raise ValueError(f"No feature rows for date {target_date.date()}")

    filtered = sliced[~sliced["symbol"].apply(_is_st_or_star)]
    filtered = filtered.copy()
    filtered["predicted_return"] = filtered["feature_momentum"].fillna(0.0)
    ranked = filtered.sort_values("predicted_return", ascending=False).head(top_n)
    ranked = ranked.assign(rank=range(1, len(ranked) + 1))

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = target_date.strftime("%Y%m%d")
        ranked.to_csv(output_dir / f"{date_str}.csv", index=False)
        ranked.to_json(output_dir / f"{date_str}.json", orient="records", force_ascii=False, indent=2)

    return ranked


def evaluate_previous_day(
    current_date: pd.Timestamp,
    recommendations_dir: Path,
    feature_df: pd.DataFrame,
    top_n: int = 10,
    report_dir: Path | None = None,
) -> dict | None:
    """评估前一日推荐的命中率与接近度。

    若没有上一日推荐文件，则返回 None。
    """
    prev_date = current_date - timedelta(days=1)
    prev_str = prev_date.strftime("%Y%m%d")
    rec_path = recommendations_dir / f"{prev_str}.csv"
    if not rec_path.exists():
        logger.info("No previous recommendation file found: %s", rec_path)
        return None

    rec_df = pd.read_csv(rec_path)
    rec_df["date"] = pd.to_datetime(prev_date)

    actual_df = feature_df[feature_df["date"] == prev_date][["symbol", "label_next"]].rename(
        columns={"label_next": "actual_return"}
    )
    actual_df = actual_df.assign(date=prev_date)
    if actual_df.empty:
        logger.info("No actual returns for %s, skip evaluation", prev_str)
        return None

    metrics, daily = evaluate_top_k(rec_df, actual_df, top_n=top_n)

    if report_dir:
        generate_report(metrics, daily, report_dir, prev_date)

    return metrics


def run_pipeline(
    date: pd.Timestamp,
    symbols: list[str],
    cache_dir: Path,
    recommendations_dir: Path,
    report_dir: Path,
    window: int = 30,
    skip_training: bool = False,
    dry_run: bool = False,
    freeze_layers: int = 0,
) -> dict:
    """执行全流程，返回摘要结果（便于测试与日志）。"""
    if dry_run:
        data_map = _synthetic_history(date, symbols, days=window + 5)
    else:
        data_map = incremental_update(symbols, date, cache_dir)

    features = recompute_features_labels(data_map, window=window)

    model = None
    train_meta: dict | None = None
    if not skip_training:
        model, train_meta = warm_start_incremental_train(
            checkpoint_dir=Path("runs/mtl"),
            freeze_layers=freeze_layers,
            epochs=1,
            dry_run=dry_run,
        )

    rec_df = generate_recommendations(features, date, output_dir=recommendations_dir)
    eval_metrics = evaluate_previous_day(date, recommendations_dir, features, report_dir=report_dir)

    return {
        "features": features,
        "recommendations": rec_df,
        "evaluation": eval_metrics,
        "model": model,
        "train_meta": train_meta,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日增量Pipeline")
    parser.add_argument("--date", required=True, help="交易日 YYYYMMDD")
    parser.add_argument("--symbols", nargs="+", default=["000001.SZ", "000002.SZ", "600519.SH"])
    parser.add_argument("--cache-dir", default="data/cache", help="缓存目录")
    parser.add_argument("--recommendations-dir", default="data/recommendations", help="推荐输出目录")
    parser.add_argument("--report-dir", default="data/recommendations/validation", help="评估输出目录")
    parser.add_argument("--window", type=int, default=30, help="滚动窗口大小")
    parser.add_argument("--skip-training", action="store_true", help="跳过增量训练")
    parser.add_argument("--dry-run", action="store_true", help="使用合成数据快速运行")
    parser.add_argument("--freeze-layers", type=int, default=0, help="冻结前K个encoder层")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    date = _to_timestamp(args.date)

    summary = run_pipeline(
        date=date,
        symbols=args.symbols,
        cache_dir=Path(args.cache_dir),
        recommendations_dir=Path(args.recommendations_dir),
        report_dir=Path(args.report_dir),
        window=args.window,
        skip_training=args.skip_training,
        dry_run=args.dry_run,
        freeze_layers=args.freeze_layers,
    )

    msg = {
        "date": date.strftime("%Y-%m-%d"),
        "recommendations": len(summary["recommendations"]),
        "evaluation": summary["evaluation"],
        "skip_training": args.skip_training,
        "dry_run": args.dry_run,
    }
    print(json.dumps(msg, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI 入口
    main()
