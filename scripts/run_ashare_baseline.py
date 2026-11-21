"""Build and run a frozen, exchange-calendar A-share baseline offline."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_infra.data.managed_daily import capture_execution_bars, days, read_calendar
from ashare_infra.data_ops import Layout, _require_space, _symbols, _token, write_lock
from ashare_infra.lake.r4_contract import make_r4_datalake
from ashare_lab import research_baseline as study
from ashare_lab.features.contract import FeatureContractLoader

ROOT = Path(__file__).resolve().parents[1]


def capture_raw(layout, cache, symbols, lake, after, through):
    import requests

    with write_lock(layout), requests.Session() as session:
        token = _token(layout.root)
        for symbol in symbols:
            _require_space(layout)
            qfq = lake.load_cached_tushare_bars(symbol, after.date(), through.date())
            if qfq.empty:
                raise ValueError(
                    f"{symbol}: adjusted cache is required before collecting raw prices"
                )
            capture_execution_bars(cache, symbol, after, through, token, session, qfq.index)


@dataclass(frozen=True)
class StudyData:
    sessions: pd.DatetimeIndex
    timing: pd.DataFrame
    panel: pd.DataFrame
    sequences: np.ndarray
    raw_bars: dict[str, pd.DataFrame]
    hashes: dict
    contract: object


def load_study_data(start, through, raw_after, *, cache=None, collect_raw=False):
    layout = Layout(ROOT)
    cache = cache or layout.cache
    calendar_dir = cache / "tushare_calendar"
    calendar = read_calendar(calendar_dir / "sse.json")
    if missing := set(days(start.date(), through.date())) - calendar.keys():
        raise ValueError(f"missing SSE calendar dates starting at {min(missing)}")
    sessions = pd.DatetimeIndex(
        pd.Timestamp(day)
        for day, opened in sorted(calendar.items())
        if opened and start.date() <= day <= through.date()
    )
    if raw_after not in sessions or len(sessions) < 52:
        raise ValueError("execution anchor must be a trading session with enough history")
    suspension_path = calendar_dir / "suspensions.json"
    suspensions = json.loads(suspension_path.read_text(encoding="utf-8"))
    timing = study.make_timing(sessions)
    contract = FeatureContractLoader.load(ROOT / "inputs/configs/features/mainline_11d_v1.toml")
    lake = make_r4_datalake(cache)
    symbols = _symbols(layout, None)
    if collect_raw:
        capture_raw(layout, cache, symbols, lake, raw_after, through)
    panels, sequences, raw_bars, hashes = [], [], {}, {}
    required_raw = ["open", "close", "pre_close", "volume"]
    for symbol in symbols:
        qfq = lake.load_cached_tushare_bars(symbol, start.date(), through.date())
        raw = lake.load_cached_tushare_bars(symbol, raw_after.date(), through.date(), adjust="raw")
        confirmed = pd.DatetimeIndex(pd.to_datetime(suspensions.get(symbol, [])))
        if qfq.empty or raw.empty or set(required_raw) - set(raw):
            raise ValueError(f"{symbol}: canonical qfq and unadjusted execution cache required")
        if (
            not raw.index.equals(qfq.loc[raw_after:through].index)
            or not np.isfinite(raw[required_raw]).all().all()
            or not (raw[required_raw] > 0).all().all()
        ):
            raise ValueError(f"{symbol}: invalid or mismatched execution bars")
        panel, windows = study.build_symbol_panel(
            symbol, qfq, sessions, confirmed, contract, timing
        )
        panels.append(panel)
        sequences.append(windows)
        raw_bars[symbol] = raw
        hashes[symbol] = {"qfq": study.frame_hash(qfq), "raw": study.frame_hash(raw)}

    return StudyData(
        sessions,
        timing,
        pd.concat(panels, ignore_index=True),
        np.concatenate(sequences),
        raw_bars,
        hashes,
        contract,
    )


def write_comparison(out, holdout, predictions, raw_bars, after, through):
    holdout = holdout.drop(columns=["split", "momentum"], errors="ignore")
    outputs = []
    for model, values in predictions.items():
        if not np.isfinite(values).all():
            raise ValueError(f"non-finite holdout predictions: {model}")
        outputs.append(holdout.assign(model=model, **dict(zip(study.PREDS, values.T, strict=True))))
    oos = pd.concat(outputs, ignore_index=True)
    oos.to_parquet(out / "oos.parquet", index=False)
    metrics = study.daily_metrics(oos, through)
    metrics.to_csv(out / "daily_metrics.csv", index=False)
    forecast = metrics.groupby(["model", "horizon"], as_index=False).agg(
        days=("date", "nunique"),
        samples=("samples", "sum"),
        mean_ic=("ic", "mean"),
        mean_rank_ic=("rank_ic", "mean"),
    )
    forecast.to_csv(out / "forecast_comparison.csv", index=False)
    last_entry = holdout.entry_at.max().tz_localize(None).normalize()
    replay = study.replay_rankings(oos, raw_bars, out, after, last_entry)
    replay.to_csv(out / "policy_comparison.csv", index=False)
    return metrics, forecast, replay


def run(args):
    start, through, after = map(pd.Timestamp, (args.start, args.through, args.holdout_after))
    if not start < after < through or args.validation_sessions < 1:
        raise ValueError("require start < holdout-after < through and positive validation sessions")
    out = args.output_dir
    if out.exists():
        raise ValueError("choose a new output directory for the baseline run")
    data = load_study_data(
        start, through, after, cache=args.cache_dir, collect_raw=args.capture_raw
    )
    panel, contract = data.panel, data.contract
    train, valid, test, freeze_at = study.frozen_split(
        panel, data.sessions, after, args.validation_sessions
    )
    out.mkdir(parents=True)
    panel["split"] = np.select(
        [train, valid, test], ["train", "validation", "holdout"], default="purged"
    )
    predictions, training = study.fit_baselines(
        panel, data.sequences, train, valid, test, contract.feature_names, args.seed
    )
    holdout = panel.loc[test]
    panel.to_parquet(out / "sample_calendar.parquet", index=False)
    metrics, forecast, replay = write_comparison(
        out, holdout, predictions, data.raw_bars, after, through
    )
    summary = {
        "data_start": start,
        "cache_through": through,
        "frozen_at": freeze_at,
        "forecast_window": [metrics.date.min(), metrics.date.max()],
        "policy_execution_window": [holdout.entry_at.min(), holdout.entry_at.max()],
        "split_rows": panel["split"].value_counts().to_dict(),
        "contract": contract.to_metadata(),
        "feature_override": "macd_hist divided by previous session close",
        "label_mode": "next_open_to_open; complete exchange-session window",
        "availability": "historical schedule assumption: next calendar day at 14:30 Asia/Shanghai",
        "universe": "R4 research pool v1 fixed before the holdout",
        "execution": "raw opening prints, 100-share lot, T+1, 10% main-board limit proxy",
        "portfolio": "CNY 1000000 each, 10 bps friction, CNY 5 minimum, price-only accounting",
        "ranking": "half each of cross-sectional 5d and 10d percentile ranks",
        "seed": args.seed,
        "training": training,
        "input_hashes": data.hashes,
        "calendar_sha256": study.frame_hash(data.timing),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, default=str, indent=2) + "\n", encoding="utf-8"
    )
    print(forecast.to_string(index=False), flush=True)
    print(replay.to_string(index=False), flush=True)
    print(f"Reports: {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2023-01-03")
    parser.add_argument("--holdout-after", default="2026-08-13")
    parser.add_argument("--through", default="2026-11-20")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--capture-raw", action="store_true", help="collect unadjusted prices from TuShare"
    )
    parser.add_argument("--validation-sessions", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
