"""Frozen A-share baseline with exchange-session labels and portfolio replay."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import time

import numpy as np
import pandas as pd

from ashare_exec.weight_mapper import WeightMapper
from ashare_infra.guard.metrics import information_coefficient, rank_information_coefficient
from ashare_infra.sim.engine import BacktestConfig, BacktestEngine
from ashare_lab.dataset.preprocessing import RollingRobustScaler
from ashare_lab.features.contract import FeatureFactory
from ashare_lab.labels.multi_horizon import MultiHorizonLabel

HORIZONS = (3, 5, 10)
LABELS = [f"label_{h}d" for h in HORIZONS]
PREDS = [f"pred_{h}d" for h in HORIZONS]
TZ = "Asia/Shanghai"


def _at(days, clock):
    offset = pd.Timedelta(hours=clock.hour, minutes=clock.minute)
    return pd.to_datetime(days).dt.tz_localize(TZ) + offset


def make_timing(sessions):
    timing = pd.DataFrame(index=pd.DatetimeIndex(sessions, name="date"))
    exchange_days = timing.index.to_series()
    timing["latest_bar_date"] = exchange_days.shift()
    timing["bar_available_at"] = _at(timing["latest_bar_date"] + pd.Timedelta(days=1), time(14, 30))
    timing["signal_at"] = _at(exchange_days, time(15))
    timing["entry_at"] = _at(exchange_days.shift(-1), time(9, 30))
    for horizon in HORIZONS:
        exit_day = exchange_days.shift(-horizon - 1)
        timing[f"exit_{horizon}d_at"] = _at(exit_day, time(9, 30))
        timing[f"label_{horizon}d_available_at"] = _at(
            exit_day + pd.Timedelta(days=1), time(14, 30)
        )
    return timing


def build_symbol_panel(symbol, bars, sessions, confirmed_suspensions, contract, timing):
    observed = bars.index[(bars["open"] > 0) & (bars["close"] > 0) & (bars["volume"] > 0)]
    observed = observed.difference(confirmed_suspensions)
    unexplained = sessions.difference(observed).difference(confirmed_suspensions)
    if len(unexplained):
        raise ValueError(f"{symbol}: unexplained missing sessions: {unexplained[:5].date.tolist()}")
    aligned = bars.loc[observed].reindex(sessions)
    features = FeatureFactory.compute(aligned, contract)
    if "macd_hist" in features:
        # Cancel later common qfq rebases without changing the existing trained feature contract.
        features["macd_hist"] = features["macd_hist"] / aligned["close"].shift(1)
    windows = np.lib.stride_tricks.sliding_window_view(
        features.to_numpy(dtype=np.float32), contract.seq_len, axis=0
    ).swapaxes(1, 2)
    panel = (
        timing.join(
            MultiHorizonLabel(horizons=HORIZONS, label_mode="next_open_to_open").compute(
                aligned, sessions=sessions
            )
        )
        .iloc[contract.seq_len - 1 :]
        .copy()
    )
    usable = np.isfinite(windows).all(axis=(1, 2))
    usable &= (panel["bar_available_at"] <= panel["signal_at"]).to_numpy()
    panel = panel.loc[usable]
    panel["symbol"] = symbol
    panel["momentum"] = features.loc[panel.index, "return_20d"]
    return panel.reset_index(), windows[usable]


def frozen_split(panel, sessions, after, validation_sessions):
    train_valid = sessions[sessions <= after]
    if len(train_valid) <= validation_sessions:
        raise ValueError("insufficient pre-holdout history")
    validation_start = train_valid[-validation_sessions]
    freeze_at = after.tz_localize(TZ) + pd.Timedelta(hours=15)
    validation_at = validation_start.tz_localize(TZ) + pd.Timedelta(hours=15)
    final_label = panel[f"label_{max(HORIZONS)}d_available_at"]
    complete = panel[LABELS].notna().all(axis=1)
    train = (panel["date"] < validation_start) & (final_label < validation_at) & complete
    valid = panel["date"].between(validation_start, after) & (final_label <= freeze_at) & complete
    test = (panel["date"] > after) & panel["entry_at"].notna()
    if not all(mask.any() for mask in (train, valid, test)):
        raise ValueError("expected nonempty training, validation and holdout splits")
    return train, valid, test, freeze_at


def fit_baselines(panel, x, train, valid, test, feature_names, seed):
    from ashare_lab.models.base import PredictionData, TrainingData
    from ashare_lab.models.xgboost import XGBoostModel

    scaler = RollingRobustScaler(feature_names).fit(x[train])
    x_train, x_valid, x_test = (scaler.transform(x[mask]) for mask in (train, valid, test))
    y_train, y_valid = (panel.loc[mask, LABELS].to_numpy(np.float32) for mask in (train, valid))
    flattened = tuple(tab.reshape(len(tab), -1) for tab in (x_train, x_valid, x_test))
    print(
        f"Frozen fit: train={len(x_train)}, valid={len(x_valid)}, holdout={len(x_test)}", flush=True
    )
    print("Training XGBoost", flush=True)
    model = XGBoostModel(
        n_estimators=220, max_depth=3, learning_rate=0.03, n_jobs=4, random_seed=seed
    )
    xgb_fit = model.train(TrainingData(flattened[0], y_train, flattened[1], y_valid))
    xgb_pred = model.predict(PredictionData(flattened[2])).preds
    print("Training LSTM", flush=True)
    lstm_pred, lstm_fit = train_lstm(x_train, y_train, x_valid, y_valid, x_test, seed)
    momentum = panel.loc[test, "momentum"].to_numpy()
    return (
        {
            "momentum_20d": np.repeat(momentum[:, None], len(PREDS), axis=1),
            "xgboost": xgb_pred,
            "lstm": lstm_pred,
        },
        xgb_fit.metrics | {"lstm": lstm_fit},
    )


def train_lstm(x_train, y_train, x_valid, y_valid, x_test, seed):
    from ashare_lab.models.lstm import MtlLSTM

    def make_model():
        return MtlLSTM(
            input_dim=x_train.shape[-1],
            hidden_size=32,
            num_layers=1,
            dropout=0.0,
            pred_cols=tuple(PREDS),
            loss_weights=(1.0, 1.0, 1.0),
        )

    model, fit = fit_torch(make_model, x_train, y_train, x_valid, y_valid, seed, patience=4)
    return predict_torch(model, x_test), fit


def _returns_tensor(model, features):
    import torch

    values = model(features)
    return torch.stack([values[name] for name in PREDS], dim=1)


def fit_torch(
    make_model,
    x_train,
    y_train,
    x_valid,
    y_valid,
    seed,
    *,
    epochs=18,
    batch_size=512,
    patience=None,
    cosine_min_lr=None,
    on_epoch=None,
):
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(min(torch.get_num_threads(), 4))
    model = make_model().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=0.001)
    scheduler = (
        torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=cosine_min_lr)
        if cosine_min_lr is not None
        else None
    )
    loss = nn.SmoothL1Loss(beta=0.02)

    def tensor(x):
        return torch.tensor(x, dtype=torch.float32, device=device)

    train_loader = DataLoader(
        TensorDataset(tensor(x_train), tensor(y_train)),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )
    validation = tensor(x_valid), tensor(y_valid)
    best, best_epoch, state = float("inf"), 0, None
    for epoch in range(1, epochs + 1):
        model.train()
        for features, target in train_loader:
            opt.zero_grad()
            loss(_returns_tensor(model, features), target).backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.inference_mode():
            val = loss(_returns_tensor(model, validation[0]), validation[1]).item()
        if val < best:
            best, best_epoch = val, epoch
            state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        if on_epoch is not None:
            on_epoch(epoch, opt.param_groups[0]["lr"], val, best_epoch, state)
        if patience is not None and epoch - best_epoch >= patience:
            break
        if scheduler is not None:
            scheduler.step()
    if state is None:
        raise ValueError("model did not produce a finite validation loss")
    model.load_state_dict(state)
    return model, {
        "best_epoch": best_epoch,
        "validation_loss": best,
        "device": str(device),
        "epochs": epoch,
        "optimizer_steps": epoch * len(train_loader),
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
    }


def predict_torch(model, values):
    import torch

    model.eval()
    device = next(model.parameters()).device
    with torch.inference_mode():
        features = torch.tensor(values, dtype=torch.float32, device=device)
        return _returns_tensor(model, features).cpu().numpy()


def daily_metrics(oos, through):
    # One common date range for all horizons, with each horizon masking its own invalid labels.
    mature = oos[oos[f"exit_{max(HORIZONS)}d_at"].dt.date <= through.date()]
    rows = []
    for (model, day), group in mature.groupby(["model", "date"]):
        for horizon, pred, label in zip(HORIZONS, PREDS, LABELS, strict=True):
            pairs = group[[pred, label]].dropna()
            if len(pairs) < 3:
                continue
            x, y = pairs[pred].to_numpy(), pairs[label].to_numpy()
            rows.append(
                {
                    "model": model,
                    "date": day,
                    "horizon": horizon,
                    "samples": len(pairs),
                    "ic": information_coefficient(x, y),
                    "rank_ic": rank_information_coefficient(x, y),
                }
            )
    if not rows:
        raise ValueError("holdout contains no mature labels")
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class ReplayRanking:
    by_execution_day: dict
    mapper: WeightMapper

    def target_weights_with_positions(self, today, current_positions):
        ranking = self.by_execution_day.get(today)
        if ranking is None:
            return None
        return self.mapper.map_weights(ranking, current_positions=current_positions)


def replay_rankings(oos, raw_bars, out, after, through):
    config = BacktestConfig(initial_cash=1_000_000)
    engine = BacktestEngine(config)
    raw_bars = {symbol: frame.loc[after:through] for symbol, frame in raw_bars.items()}
    results = []
    for model, group in oos.groupby("model"):
        group = group.assign(
            execution_day=group["entry_at"].dt.tz_localize(None).dt.normalize(),
            rank_score=group.groupby("date")["pred_5d"].rank(pct=True) * 0.5
            + group.groupby("date")["pred_10d"].rank(pct=True) * 0.5,
        )
        ranking = {
            day: list(
                rows.sort_values(["rank_score", "symbol"], ascending=[False, True])[
                    ["symbol", "rank_score"]
                ].itertuples(index=False, name=None)
            )
            for day, rows in group.groupby("execution_day")
        }
        for policy, retention_rank in (("fixed_top10", None), ("retain_top15", 15)):
            strategy = ReplayRanking(ranking, WeightMapper(top_n=10, retention_rank=retention_rank))
            result = engine.run(raw_bars, strategy)
            stem = f"{model}_{policy}"
            result.equity_curve.to_csv(out / f"{stem}_equity.csv")
            result.fills.to_csv(out / f"{stem}_fills.csv", index=False)
            if not result.fills.empty:
                fills = result.fills.assign(
                    date=pd.to_datetime(result.fills["date"]),
                    delta=result.fills["shares"].where(
                        result.fills["side"].eq("BUY"), -result.fills["shares"]
                    ),
                )
                positions = fills.groupby(["date", "symbol"])["delta"].sum().unstack(fill_value=0)
                positions.reindex(result.equity_curve.index, fill_value=0).cumsum().to_csv(
                    out / f"{stem}_positions.csv"
                )
            equity = pd.concat([pd.Series([config.initial_cash]), result.equity_curve["equity"]])
            results.append(
                {
                    "model": model,
                    "policy": policy,
                    "net_return": equity.iloc[-1] / equity.iloc[0] - 1,
                    "max_drawdown": (equity / equity.cummax() - 1).min(),
                    "turnover_multiple": result.stats["turnover_ratio"],
                    "fees": result.stats["total_cost"],
                    "fills": len(result.fills),
                    **result.diagnostics,
                }
            )
    return pd.DataFrame(results)


def frame_hash(frame):
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()
    ).hexdigest()
