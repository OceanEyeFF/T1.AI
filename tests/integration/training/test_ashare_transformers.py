from dataclasses import asdict
from datetime import date, timedelta
from math import cos, pi
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ashare_infra.ops_backup import digest
from ashare_lab import research_baseline as study
from ashare_lab.dataset.preprocessing import RollingRobustScaler
from ashare_lab.models.transformer import MTLTransformer, create_mtl_model
from ashare_lab.trend_schema import PRIMARY_TREND_PRED_COLS
from scripts import run_ashare_transformers as experiment
from scripts.run_ashare_transformers import configs, final_window


@pytest.mark.parametrize("depth", [2, 4, 6, 8, 10])
def test_horizon_queries_cross_attend_and_predictions_ignore_targets(depth):
    config = configs(11, 20)[f"encoder_decoder_3_{depth}"]
    model = create_mtl_model(**(asdict(config) | {"dropout": 0})).eval()
    x = torch.randn(2, 20, 11)
    captured = {}

    def capture_decoder(_module, args):
        captured["query"] = args[0]
        captured["memory"] = args[1]

    handler = model.transformer_decoder.register_forward_pre_hook(capture_decoder)
    predictions = model(x)
    with_other_targets, losses = model(x, labels=torch.full((2, 3), 0.1))
    handler.remove()
    assert len(model.transformer_encoder.layers) == 3
    assert len(model.transformer_decoder.layers) == depth
    assert captured["query"].shape == (2, 3, config.d_model)
    assert captured["memory"].shape == (2, 20, config.d_model)
    assert list(predictions) == list(PRIMARY_TREND_PRED_COLS)
    for name, prediction in predictions.items():
        assert prediction.shape == (2,)
        torch.testing.assert_close(prediction, with_other_targets[name])
    losses["total"].backward()
    assert (model.horizon_queries.grad.abs().sum(dim=1) > 0).all()


def test_comparison_has_nearly_equal_parameter_counts_and_loads_legacy_state():
    profiles = configs(11, 20)
    comparison = {name: MTLTransformer(config) for name, config in profiles.items()}
    counts = {
        name: sum(parameter.numel() for parameter in model.parameters())
        for name, model in comparison.items()
    }
    matched = [size for name, size in counts.items() if not name.endswith("_2x")]
    assert max(matched) / min(matched) < 1.05
    for name in experiment.SCALING_MODELS["width"]:
        original = name.removesuffix("_2x")
        assert counts[name] / counts[original] == pytest.approx(2, rel=0.01)
        assert profiles[name].n_decoder_layers == profiles[original].n_decoder_layers
        assert profiles[name].d_model > profiles[original].d_model
    encoder = comparison["encoder_only"]
    same = MTLTransformer(configs(11, 20)["encoder_only"])
    same.load_state_dict(encoder.state_dict(), strict=True)
    assert not any(
        key.startswith(("horizon_queries", "transformer_decoder")) for key in encoder.state_dict()
    )


def test_final_reserve_requires_the_full_session_tail_and_clips_extra_dates():
    after = pd.Timestamp("2026-11-20")
    start = date(2026, 11, 21)
    calendar = {
        day: day.weekday() < 5 for day in (start + timedelta(days=offset) for offset in range(110))
    }
    future = [day for day, open_day in calendar.items() if open_day]
    short = {day: status for day, status in calendar.items() if day < future[70]}
    with pytest.raises(ValueError, match="70/71"):
        final_window(short, after, 60, 11)
    dates, end = final_window(calendar, after, 60, 11)
    assert list(dates.date) == future[:60]
    assert end.date() == future[70]


def test_long_fit_uses_cosine_and_keeps_best_before_early_stop(tmp_path, monkeypatch):
    class FlatReturns(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.bias = torch.nn.Parameter(torch.zeros(()))

        def forward(self, inputs):
            return {head: self.bias.expand(len(inputs)) for head in study.PREDS}

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    x = np.zeros((2, 20, 11), dtype=np.float32)
    target = np.zeros((2, 3), dtype=np.float32)
    history = []
    checkpoint = tmp_path / "cosine8.pt"
    _, fit = study.fit_torch(
        FlatReturns,
        x,
        target,
        x,
        target,
        42,
        epochs=32,
        batch_size=2,
        patience=8,
        cosine_min_lr=0.00001,
        on_epoch=experiment._cosine_epoch_log("flat", 42, history, checkpoint),
    )
    assert (fit["epochs"], fit["best_epoch"], fit["optimizer_steps"]) == (9, 1, 9)
    assert history[0]["learning_rate"] == pytest.approx(0.001)
    expected = 0.00001 + (0.001 - 0.00001) * (1 + cos(pi * 7 / 32)) / 2
    assert history[7]["learning_rate"] == pytest.approx(expected)
    assert torch.load(checkpoint, weights_only=True)["bias"].item() == 0.0


def test_final_loads_sealed_checkpoint_and_scores_only_reserved_signals(tmp_path, monkeypatch):
    future = pd.bdate_range("2026-11-23", periods=14)
    panel = pd.DataFrame({"date": future, "momentum": np.linspace(0.01, 0.1, len(future))})
    x = np.random.default_rng(7).normal(size=(len(panel), 20, 11)).astype(np.float32)
    names = tuple(f"x{i}" for i in range(11))
    scaler = RollingRobustScaler(names).fit(x[:4])
    scaler_path = tmp_path / "scaler.json"
    experiment._json(scaler_path, scaler.to_dict())
    config = configs(11, 20)["encoder_decoder_3_2"]
    checkpoint = tmp_path / "model.pt"
    torch.save(MTLTransformer(config).state_dict(), checkpoint)
    seal = tmp_path / "seal.json"
    experiment._json(
        seal,
        {
            "protocol": 1,
            "start_after": "2026-11-20",
            "signal_sessions": 2,
            "label_tail_sessions": 11,
            "data_start": "2023-01-03",
            "contract_hash": "fixture",
            "symbols": ["600000.SH"],
            "fit_cutoff": "2026-08-13",
            "model_configs": {"ed": asdict(config)},
            "scaler": {"path": str(scaler_path), "sha256": digest(scaler_path)},
            "checkpoints": {"ed": [{"path": str(checkpoint), "sha256": digest(checkpoint)}]},
        },
    )
    monkeypatch.setattr(experiment, "read_calendar", lambda _: dict.fromkeys(future.date, True))
    data = SimpleNamespace(
        panel=panel,
        sequences=x,
        raw_bars={"600000.SH": None},
        contract=SimpleNamespace(feature_names=names, contract_hash="fixture"),
    )
    monkeypatch.setattr(experiment, "load_study_data", lambda *args, **kwargs: data)

    def capture_report(_out, _data, predictions, holdout, _after, through, summary):
        assert list(holdout["date"]) == list(future[:2])
        assert through == future[12]
        assert set(predictions) == {"momentum_20d", "ed"}
        assert predictions["ed"].shape == (2, 3)
        assert summary["phase"] == "final"

    monkeypatch.setattr(experiment, "_evaluate", capture_report)
    args = SimpleNamespace(
        final_from=seal,
        cache_dir=tmp_path,
        output_dir=tmp_path / "final",
        capture_raw=False,
    )
    experiment.final(args)
    assert args.output_dir.is_dir()
    checkpoint.write_bytes(b"altered")
    args.output_dir = tmp_path / "tampered"
    with pytest.raises(ValueError, match="sealed artifact changed"):
        experiment.final(args)
    assert not args.output_dir.exists()
