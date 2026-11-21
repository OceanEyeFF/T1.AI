"""Compare the encoder-only and three-query transformers, then seal a future test."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ashare_infra.data.managed_daily import read_calendar
from ashare_infra.data_ops import Layout
from ashare_infra.ops_backup import digest
from ashare_lab import research_baseline as study
from ashare_lab.dataset.preprocessing import RollingRobustScaler
from ashare_lab.models.transformer import MTLTransformer, TransformerConfig
from scripts.run_ashare_baseline import ROOT, load_study_data, write_comparison

START, FREEZE, EXPLORATORY_END = map(pd.Timestamp, ("2023-01-03", "2026-08-13", "2026-11-20"))
SEEDS = (42, 43, 44)
EPOCHS, BATCH_SIZE, FINAL_SESSIONS = 8, 512, 60
BASELINE_MODELS = ("encoder_only", "encoder_decoder_3_2")
DEEPER_MODELS = ("encoder_decoder_3_4", "encoder_decoder_3_6")
LONG_FIT_MODELS = {
    "depth": ("encoder_decoder_3_6", "encoder_decoder_3_8", "encoder_decoder_3_10"),
    "narrow": ("encoder_decoder_3_2", "encoder_decoder_3_4"),
    "width": ("encoder_decoder_3_2_2x", "encoder_decoder_3_4_2x"),
}
LONG_EPOCHS, LONG_PATIENCE, COSINE_MIN_LR = 32, 8, 0.00001
SCALING_MODELS = {
    "width": tuple(f"encoder_decoder_3_{depth}_2x" for depth in (2, 4, 6)),
    "depth": ("encoder_decoder_3_8", "encoder_decoder_3_10"),
}


def configs(input_dim, seq_len):
    inputs = {
        "input_dim": input_dim,
        "n_heads": 4,
        "dropout": 0.1,
        "max_seq_len": seq_len,
        "min_seq_len": seq_len,
    }
    # (Decoder layers, hidden width, feed-forward width), matched by measured parameters.
    profiles = {
        "3_2": (2, 32, 64),
        "3_4": (4, 28, 37),
        "3_6": (6, 24, 33),
        "3_2_2x": (2, 44, 104),
        "3_4_2x": (4, 40, 53),
        "3_6_2x": (6, 32, 67),
        "3_8": (8, 20, 42),
        "3_10": (10, 20, 23),
    }
    models = {"encoder_only": TransformerConfig(**inputs, d_model=32, n_layers=4, d_ff=128)}
    for name, (depth, hidden, feed_forward) in profiles.items():
        models[f"encoder_decoder_{name}"] = TransformerConfig(
            **inputs, d_model=hidden, n_layers=3, d_ff=feed_forward, n_decoder_layers=depth
        )
    return models


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def _momentum(holdout):
    return {
        "momentum_20d": np.repeat(holdout["momentum"].to_numpy()[:, None], len(study.PREDS), axis=1)
    }


def _seed_metrics(holdout, name, predicted, seed):
    panel = holdout.assign(model=name, **dict(zip(study.PREDS, predicted.T, strict=True)))
    return study.daily_metrics(panel, EXPLORATORY_END).assign(seed=seed)


def _cosine_epoch_log(name, seed, history, checkpoint):
    def record(epoch, lr, val, best_epoch, state):
        history.append(
            {
                "model": name,
                "seed": seed,
                "epoch": epoch,
                "learning_rate": lr,
                "validation_loss": val,
                "best_epoch": best_epoch,
            }
        )
        if epoch == EPOCHS:
            torch.save(state, checkpoint)
        if epoch % 4 == 0:
            print(f"{name} seed {seed} epoch {epoch}: val={val:.7f}, best={best_epoch}", flush=True)

    return record


def _evaluate(out, data, predictions, holdout, after, through, summary):
    metrics, forecast, replay = write_comparison(
        out, holdout, predictions, data.raw_bars, after, through
    )
    summary |= {
        "forecast_window": [metrics.date.min(), metrics.date.max()],
        "policy_execution_window": [holdout.entry_at.min(), holdout.entry_at.max()],
        "candidate_rows_per_model": len(holdout),
        "input_hashes": data.hashes,
        "calendar_sha256": study.frame_hash(data.timing),
    }
    _json(out / "summary.json", summary)
    print(forecast.to_string(index=False), flush=True)
    print(replay.to_string(index=False), flush=True)
    print(f"Reports: {out}", flush=True)


def explore(args):
    data = load_study_data(
        START, EXPLORATORY_END, FREEZE, cache=args.cache_dir, collect_raw=args.capture_raw
    )
    validation_sessions = 60
    train, valid, test, frozen_at = study.frozen_split(
        data.panel, data.sessions, FREEZE, validation_sessions
    )
    contract = data.contract
    timing_hash = study.frame_hash(data.timing)
    if args.reference:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        if (
            reference["input_hashes"] != data.hashes
            or reference["calendar_sha256"] != timing_hash
            or reference["contract"]["feature_contract_hash"] != contract.contract_hash
        ):
            raise ValueError(
                "cache, calendar or feature contract differs from the baseline snapshot"
            )
    holdout = data.panel.loc[test]
    scaler = RollingRobustScaler(contract.feature_names).fit(data.sequences[train])
    xt, xv, xo = (scaler.transform(data.sequences[split]) for split in (train, valid, test))
    yt, yv = (data.panel.loc[split, study.LABELS].to_numpy(np.float32) for split in (train, valid))
    available = configs(contract.input_dim, contract.seq_len)
    comparison = SCALING_MODELS.get(args.scaling, DEEPER_MODELS if args.deeper else BASELINE_MODELS)
    epochs = EPOCHS
    if args.long_fit:
        comparison = LONG_FIT_MODELS[args.long_fit]
        epochs = LONG_EPOCHS
    models = {name: available[name] for name in comparison}
    out = args.output_dir.resolve()
    checkpoints = args.checkpoint_dir.resolve()
    if out.exists() or checkpoints.exists():
        raise ValueError("choose new report and checkpoint directories")
    # A single scaler is fitted to the training split and frozen with all model checkpoints.
    out.mkdir(parents=True)
    checkpoints.mkdir(parents=True)
    scaler_path = checkpoints / "scaler.json"
    _json(scaler_path, scaler.to_dict())
    predictions = _momentum(holdout)
    metrics_by_seed = []
    training = {}
    members = {}
    history = []
    for name, config in models.items():
        seed_results = []
        control_results = []
        for seed in SEEDS:
            print(f"Training {name} seed {seed}", flush=True)
            settings = {}
            if args.long_fit:
                control = checkpoints / f"{name}_cosine8_{seed}.pt"
                settings = {
                    "patience": LONG_PATIENCE,
                    "cosine_min_lr": COSINE_MIN_LR,
                    "on_epoch": _cosine_epoch_log(name, seed, history, control),
                }
            model, fit = study.fit_torch(
                partial(MTLTransformer, config),
                xt,
                yt,
                xv,
                yv,
                seed,
                epochs=epochs,
                batch_size=BATCH_SIZE,
                **settings,
            )
            path = checkpoints / f"{name}_{seed}.pt"
            torch.save(model.state_dict(), path)
            members.setdefault(name, []).append(
                {"seed": seed, "path": str(path), "sha256": digest(path)}
            )
            training.setdefault(name, []).append({"seed": seed, **fit})
            predicted = study.predict_torch(model, xo)
            seed_results.append(predicted)
            metrics_by_seed.append(_seed_metrics(holdout, name, predicted, seed))
            if args.long_fit:
                model.load_state_dict(torch.load(control, map_location="cpu", weights_only=True))
                short_prediction = study.predict_torch(model, xo)
                control_results.append(short_prediction)
                metrics_by_seed.append(
                    _seed_metrics(holdout, f"{name}_cosine8", short_prediction, seed)
                )
            print(f"{name} seed {seed}: {fit}", flush=True)
        predictions[name] = np.mean(seed_results, axis=0)
        if control_results:
            predictions[f"{name}_cosine8"] = np.mean(control_results, axis=0)
    counts = [runs[0]["parameters"] for runs in training.values()]
    if max(counts) / min(counts) > 1.05:
        raise ValueError("Transformer comparison exceeds the 5% parameter matching tolerance")
    seal = {
        "protocol": 1,
        "phase": "awaiting_new_data",
        "start_after": EXPLORATORY_END.date().isoformat(),
        "signal_sessions": FINAL_SESSIONS,
        "label_tail_sessions": max(study.HORIZONS) + 1,
        "fit_cutoff": frozen_at.isoformat(),
        "data_start": START.date().isoformat(),
        "contract_hash": contract.contract_hash,
        "symbols": sorted(data.raw_bars),
        "model_configs": {name: asdict(config) for name, config in models.items()},
        "scaler": {"path": str(scaler_path), "sha256": digest(scaler_path)},
        "checkpoints": members,
        "seeds": SEEDS,
        "prediction_aggregation": "mean return prediction across the three seeds",
        "decision_policies": ["fixed_top10", "retain_top15"],
        "primary_forecast_metric": "mean daily RankIC averaged over 5d and 10d",
        "estimation": "frozen models, no fit or selection on final-window data",
    }
    _json(out / "final_validation.json", seal)
    pd.concat(metrics_by_seed).to_csv(out / "daily_metrics_by_seed.csv", index=False)
    budget = {
        "epochs": epochs,
        "batch_size": BATCH_SIZE,
        "seeds": SEEDS,
        "loss": "SmoothL1(beta=0.02)",
        "optimizer": "AdamW(lr=0.001)",
    }
    if args.long_fit:
        pd.DataFrame(history).to_csv(out / "training_history.csv", index=False)
        budget |= {
            "scheduler": "CosineAnnealingLR",
            "eta_min": COSINE_MIN_LR,
            "early_stop_patience": LONG_PATIENCE,
            "control_epochs": EPOCHS,
        }
    _evaluate(
        out,
        data,
        predictions,
        holdout,
        FREEZE,
        EXPLORATORY_END,
        {
            "phase": "exploratory",
            "scaling_axis": args.scaling,
            "long_fit_cohort": args.long_fit,
            "fit_cutoff": frozen_at,
            "training": training,
            "budget": budget,
            "validation_sessions": validation_sessions,
            "reference_verified": bool(args.reference),
        },
    )


def final_window(calendar, after, signal_count, tail_count):
    future = pd.DatetimeIndex(
        [pd.Timestamp(day) for day in sorted(calendar) if calendar[day] and day > after.date()]
    )
    required = signal_count + tail_count
    if len(future) < required:
        raise ValueError(
            f"final window not mature: {len(future)}/{required} post-cutoff trading sessions cached "
            f"({signal_count} signal sessions + {tail_count} label-maturity sessions)"
        )
    return future[:signal_count], future[required - 1]


def _verified_path(member):
    path = Path(member["path"])
    if digest(path) != member["sha256"]:
        raise ValueError(f"sealed artifact changed: {path}")
    return path


def final(args):
    seal = json.loads(args.final_from.read_text(encoding="utf-8"))
    if seal["protocol"] != 1:
        raise ValueError("unsupported final validation protocol")
    cache = args.cache_dir or Layout(ROOT).cache
    after = pd.Timestamp(seal["start_after"])
    signal_dates, through = final_window(
        read_calendar(cache / "tushare_calendar/sse.json"),
        after,
        seal["signal_sessions"],
        seal["label_tail_sessions"],
    )
    out = args.output_dir.resolve()
    if out.exists():
        raise ValueError("choose a new final report directory")
    scaler = RollingRobustScaler.from_dict(
        json.loads(_verified_path(seal["scaler"]).read_text(encoding="utf-8"))
    )
    model_paths = {
        name: [_verified_path(member) for member in entries]
        for name, entries in seal["checkpoints"].items()
    }
    data = load_study_data(
        pd.Timestamp(seal["data_start"]), through, after, cache=cache, collect_raw=args.capture_raw
    )
    if (
        data.contract.contract_hash != seal["contract_hash"]
        or tuple(data.contract.feature_names) != scaler.feature_names
        or sorted(data.raw_bars) != seal["symbols"]
    ):
        raise ValueError("protocol inputs differ from the sealed model inputs")
    selected = data.panel["date"].isin(signal_dates)
    holdout = data.panel.loc[selected]
    if not pd.DatetimeIndex(sorted(holdout.date.unique())).equals(signal_dates):
        raise ValueError("not every final signal date has usable data")
    x = scaler.transform(data.sequences[selected])
    predictions = _momentum(holdout)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    for name, paths in model_paths.items():
        model = MTLTransformer(TransformerConfig(**seal["model_configs"][name])).to(device)
        seed_predictions = []
        for path in paths:
            model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
            seed_predictions.append(study.predict_torch(model, x))
        predictions[name] = np.mean(seed_predictions, axis=0)
    out.mkdir(parents=True)
    _evaluate(
        out,
        data,
        predictions,
        holdout,
        after,
        through,
        {
            "phase": "final",
            "seal_sha256": digest(args.final_from),
            "fit_cutoff": seal["fit_cutoff"],
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--checkpoint-dir", type=Path, help="train and save exploratory checkpoints")
    mode.add_argument(
        "--final-from", type=Path, help="verify and evaluate the sealed final validation"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--reference", type=Path, help="assert exact match to a baseline summary")
    parser.add_argument("--capture-raw", action="store_true")
    cohort = parser.add_mutually_exclusive_group()
    cohort.add_argument(
        "--deeper", action="store_true", help="compare 3+4 and 3+6 on the exploratory window"
    )
    cohort.add_argument("--scaling", choices=SCALING_MODELS, help="compare width or decoder depth")
    cohort.add_argument(
        "--long-fit",
        nargs="?",
        const="depth",
        choices=LONG_FIT_MODELS,
        help="test extended cosine training on deeper models or narrow/widened 3+2 and 3+4",
    )
    args = parser.parse_args()
    if (args.deeper or args.scaling or args.long_fit) and args.final_from:
        parser.error("the final run uses its sealed manifest to choose models")
    try:
        if args.final_from:
            final(args)
        else:
            explore(args)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
