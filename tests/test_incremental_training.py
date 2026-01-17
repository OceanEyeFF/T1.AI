from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from ashare_lab.models.transformer import create_mtl_model
from ashare_lab.training.mtl_finetune import (
    IncrementalTrainConfig,
    IncrementalTrainer,
    TrainingGate,
    as_float,
    as_float_tuple3,
    as_int,
    count_labeled_samples,
    fit,
    infer_last_train_date_from_checkpoint,
    load_yaml,
    save_checkpoint_atomic,
)


def _make_tiny_model(*, input_dim: int = 3, seq_len: int = 4):
    model = create_mtl_model(
        input_dim=input_dim,
        d_model=16,
        n_layers=4,
        n_heads=4,
        d_ff=32,
        dropout=0.0,
        max_seq_len=max(seq_len, 4),
        min_seq_len=min(seq_len, 2),
        loss_weights=(1.0, 1.0, 1.0),
    )
    model.to(torch.device("cpu"))
    return model


def _make_loaders(*, n: int = 24, seq_len: int = 4, input_dim: int = 3, batch: int = 6):
    torch.manual_seed(0)
    x = torch.randn(n, seq_len, input_dim)
    y = torch.randn(n, 3)
    y[0] = torch.tensor([float("nan"), float("nan"), float("nan")])
    y[1, 1] = float("nan")
    ds = TensorDataset(x, y)
    loader = DataLoader(ds, batch_size=batch, shuffle=False)
    return loader


def test_incremental_config_parsing():
    cfg = {
        "incremental_training": {
            "enabled": True,
            "trigger_schedule": "weekly",
            "min_labeled_samples": 123,
            "freeze_layers": 2,
            "learning_rate": 5e-5,
            "weight_decay": 2e-5,
            "max_epochs": 3,
            "early_stopping_patience": 2,
            "warm_start_checkpoint": "models/latest_mtl.pt",
            "save_checkpoint": "models/latest_mtl.pt",
        }
    }
    inc = IncrementalTrainConfig.from_config_dict(cfg)
    assert inc.enabled is True
    assert inc.trigger_schedule == "weekly"
    assert inc.min_labeled_samples == 123
    assert inc.freeze_layers == 2
    assert inc.learning_rate == pytest.approx(5e-5)
    assert inc.weight_decay == pytest.approx(2e-5)
    assert inc.max_epochs == 3
    assert inc.early_stopping_patience == 2
    assert inc.warm_start_checkpoint.as_posix().endswith("models/latest_mtl.pt")
    assert inc.save_checkpoint.as_posix().endswith("models/latest_mtl.pt")

    # tolerate non-mapping incremental_training
    inc2 = IncrementalTrainConfig.from_config_dict({"incremental_training": "oops"})
    assert inc2.enabled is True


def test_count_labeled_samples():
    labels = torch.tensor(
        [
            [float("nan"), float("nan"), float("nan")],
            [1.0, float("nan"), float("nan")],
            [float("nan"), 2.0, 3.0],
        ]
    )
    assert count_labeled_samples(labels) == 2
    with pytest.raises(ValueError):
        count_labeled_samples(torch.randn(3, 2))


def test_training_gate_should_train_scenarios():
    gate = TrainingGate()

    ok, reason = gate.should_train(
        current_date="2026-01-17",
        last_train_date=None,
        schedule="weekly",
        labeled_count=100,
        min_samples=10,
    )
    assert ok is True
    assert "weekly" in reason

    ok, reason = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-12",
        schedule="weekly",
        labeled_count=100,
        min_samples=10,
    )
    assert ok is False
    assert "days_since_last" in reason

    ok, _ = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-10",
        schedule="weekly",
        labeled_count=100,
        min_samples=10,
    )
    assert ok is True

    ok, _ = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-16",
        schedule="daily",
        labeled_count=10,
        min_samples=10,
    )
    assert ok is True

    ok, reason = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-01",
        schedule="manual",
        labeled_count=10,
        min_samples=10,
    )
    assert ok is False
    assert reason == "schedule=manual"

    ok, reason = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-01",
        schedule="weekly",
        labeled_count=9,
        min_samples=10,
    )
    assert ok is False
    assert "labeled_count" in reason

    ok, reason = gate.should_train(
        current_date="2026-01-17",
        last_train_date="2026-01-01",
        schedule="unknown",
        labeled_count=10,
        min_samples=10,
    )
    assert ok is False
    assert "unknown schedule" in reason

    with pytest.raises(ValueError):
        gate.should_train(
            current_date="20260117",
            last_train_date=None,
            schedule="daily",
            labeled_count=10,
            min_samples=10,
        )


def test_save_checkpoint_atomic_roundtrip_and_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "ckpt.pt"
    payload = {"a": 1, "b": "x", "c": [1, 2, 3]}
    save_checkpoint_atomic(path, payload)
    assert path.exists()
    loaded = torch.load(path, map_location="cpu", weights_only=False)
    assert loaded["a"] == 1
    assert loaded["b"] == "x"
    assert loaded["c"] == [1, 2, 3]
    assert not list(tmp_path.glob("ckpt.pt.tmp.*"))

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("ashare_lab.training.mtl_finetune.torch.save", _boom)
    with pytest.raises(RuntimeError):
        save_checkpoint_atomic(tmp_path / "fail.pt", {"x": 1})
    assert not list(tmp_path.glob("fail.pt.tmp.*"))


def test_yaml_and_cast_helpers(tmp_path: Path):
    yml = tmp_path / "x.yaml"
    yml.write_text("a: 1\nb: [1, 2, 3]\n", encoding="utf-8")
    assert load_yaml(yml) == {"a": 1, "b": [1, 2, 3]}

    assert as_float_tuple3([1, 2, 3]) == (1.0, 2.0, 3.0)
    assert as_float_tuple3([1, 2]) == (1.0, 1.0, 1.0)

    assert as_float(None, 1.5) == 1.5
    assert as_float(2, 1.5) == 2.0
    assert as_float("3.5", 1.5) == 3.5
    assert as_float("oops", 1.5) == 1.5
    assert as_float(object(), 1.5) == 1.5

    assert as_int(None, 7) == 7
    assert as_int(3, 7) == 3
    assert as_int(3.2, 7) == 3
    assert as_int("8", 7) == 8
    assert as_int("oops", 7) == 7
    assert as_int(object(), 7) == 7


def test_infer_last_train_date_from_checkpoint():
    assert infer_last_train_date_from_checkpoint(None) is None
    assert infer_last_train_date_from_checkpoint({}) is None
    assert infer_last_train_date_from_checkpoint({"trained_at": ""}) is None
    assert infer_last_train_date_from_checkpoint({"trained_at": "2026-01-01"}) == "2026-01-01"


def test_incremental_trainer_warm_start_and_freeze(tmp_path: Path):
    seq_len = 4
    model_a = _make_tiny_model(seq_len=seq_len)
    ckpt_path = tmp_path / "warm.pt"
    save_checkpoint_atomic(ckpt_path, {"model_state_dict": model_a.state_dict(), "trained_at": "2026-01-01"})

    model_b = _make_tiny_model(seq_len=seq_len)
    loader = _make_loaders(seq_len=seq_len)
    cfg = IncrementalTrainConfig(
        enabled=True,
        trigger_schedule="daily",
        min_labeled_samples=1,
        freeze_layers=2,
        learning_rate=1e-4,
        weight_decay=0.0,
        max_epochs=1,
        early_stopping_patience=1,
        warm_start_checkpoint=ckpt_path,
        save_checkpoint=tmp_path / "out.pt",
    )
    trainer = IncrementalTrainer(cfg, model_b, loader, loader, loss_weights=(1.0, 1.0, 1.0))
    ckpt = trainer.load_warm_start_checkpoint()
    assert ckpt is not None
    model_b.load_state_dict(ckpt["model_state_dict"])
    assert torch.allclose(
        next(iter(model_a.parameters())).detach(),
        next(iter(model_b.parameters())).detach(),
    )

    trainer.freeze_encoder_layers(2)
    for p in model_b.transformer_encoder.layers[0].parameters():
        assert p.requires_grad is False
    for p in model_b.transformer_encoder.layers[2].parameters():
        assert p.requires_grad is True


def test_incremental_trainer_corrupt_checkpoint_raises(tmp_path: Path):
    model = _make_tiny_model(seq_len=4)
    loader = _make_loaders(seq_len=4)
    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"not a checkpoint")
    cfg = IncrementalTrainConfig(
        warm_start_checkpoint=bad,
        save_checkpoint=tmp_path / "out.pt",
    )
    trainer = IncrementalTrainer(cfg, model, loader, loader)
    with pytest.raises(ValueError):
        trainer.load_warm_start_checkpoint()


def test_incremental_trainer_run_skipped_by_gate(tmp_path: Path):
    model = _make_tiny_model(seq_len=4)
    loader = _make_loaders(seq_len=4)
    cfg = IncrementalTrainConfig(
        enabled=True,
        trigger_schedule="weekly",
        min_labeled_samples=1000,
        freeze_layers=1,
        learning_rate=1e-5,
        weight_decay=0.0,
        max_epochs=1,
        early_stopping_patience=1,
        warm_start_checkpoint=tmp_path / "missing.pt",
        save_checkpoint=tmp_path / "out.pt",
    )
    trainer = IncrementalTrainer(cfg, model, loader, loader)
    result = trainer.run(TrainingGate(), current_date="2026-01-17", last_train_date="2026-01-01", labeled_count=0)
    assert result["skipped"] is True
    assert "min_samples" in str(result["reason"])


def test_incremental_trainer_disabled_skips(tmp_path: Path):
    model = _make_tiny_model(seq_len=4)
    loader = _make_loaders(seq_len=4)
    cfg = IncrementalTrainConfig(
        enabled=False,
        warm_start_checkpoint=tmp_path / "missing.pt",
        save_checkpoint=tmp_path / "out.pt",
    )
    trainer = IncrementalTrainer(cfg, model, loader, loader)
    result = trainer.run(TrainingGate(), current_date="2026-01-17", last_train_date=None, labeled_count=999)
    assert result["skipped"] is True
    assert result["reason"] == "incremental_training.disabled"


def test_incremental_trainer_run_trains_and_saves(tmp_path: Path):
    seq_len = 4
    model = _make_tiny_model(seq_len=seq_len)
    train_loader = _make_loaders(seq_len=seq_len)
    val_loader = _make_loaders(seq_len=seq_len)
    out_path = tmp_path / "latest_mtl.pt"

    cfg = IncrementalTrainConfig(
        enabled=True,
        trigger_schedule="daily",
        min_labeled_samples=1,
        freeze_layers=1,
        learning_rate=5e-5,
        weight_decay=0.0,
        max_epochs=2,
        early_stopping_patience=1,
        warm_start_checkpoint=tmp_path / "missing.pt",
        save_checkpoint=out_path,
    )
    trainer = IncrementalTrainer(cfg, model, train_loader, val_loader)
    labeled_count = 0
    for _x, y in train_loader:
        labeled_count += count_labeled_samples(y)

    res = trainer.run(TrainingGate(), current_date="2026-01-17", last_train_date=None, labeled_count=labeled_count)
    assert res["skipped"] is False
    assert out_path.exists()
    assert not list(tmp_path.glob("latest_mtl.pt.tmp.*"))

    ckpt = torch.load(out_path, map_location="cpu", weights_only=False)
    assert ckpt["mode"] == "incremental"
    assert ckpt["trained_at"] == "2026-01-17"
    assert ckpt["labeled_count"] == labeled_count
    assert isinstance(ckpt["val_ic"], float)

    for p in model.transformer_encoder.layers[0].parameters():
        assert p.requires_grad is False


def test_incremental_trainer_run_warm_start_and_early_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seq_len = 4
    torch.manual_seed(123)
    model_a = _make_tiny_model(seq_len=seq_len)
    warm_path = tmp_path / "warm.pt"
    save_checkpoint_atomic(warm_path, {"model_state_dict": model_a.state_dict(), "trained_at": "2026-01-01"})

    torch.manual_seed(999)
    model_b = _make_tiny_model(seq_len=seq_len)
    train_loader = _make_loaders(seq_len=seq_len)
    out_path = tmp_path / "latest_mtl.pt"

    cfg = IncrementalTrainConfig(
        enabled=True,
        trigger_schedule="daily",
        min_labeled_samples=1,
        freeze_layers=0,
        learning_rate=0.0,  # keep params unchanged after warm-start
        weight_decay=0.0,
        max_epochs=3,
        early_stopping_patience=1,
        warm_start_checkpoint=warm_path,
        save_checkpoint=out_path,
    )
    trainer = IncrementalTrainer(cfg, model_b, train_loader, train_loader)

    monkeypatch.setattr(trainer, "validate", lambda: {"loss": 0.0, "ic": 0.0, "ic_3d": 0.0, "ic_5d": 0.0, "ic_10d": 0.0})

    labeled_count = 0
    for _x, y in train_loader:
        labeled_count += count_labeled_samples(y)

    res = trainer.run(TrainingGate(), current_date="2026-01-17", last_train_date=None, labeled_count=labeled_count)
    assert res["skipped"] is False
    assert out_path.exists()
    assert res["epochs"] >= 1
    assert torch.allclose(
        next(iter(model_a.parameters())).detach(),
        next(iter(model_b.parameters())).detach(),
    )


def test_fit_full_training_smoke(tmp_path: Path):
    seq_len = 4
    model = _make_tiny_model(seq_len=seq_len)
    loader = _make_loaders(seq_len=seq_len)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.0)

    out = fit(
        model,
        loader,
        loader,
        opt,
        loss_weights=(1.0, 1.0, 1.0),
        max_epochs=2,
        patience=1,
        model_dir=tmp_path / "models",
        log_dir=tmp_path / "logs",
        early_stopping_threshold=None,
    )
    assert "best_ic" in out
    assert Path(out["best_path"]).exists()
    assert Path(out["latest_path"]).exists()
    assert (tmp_path / "logs" / "mtl_train_log.csv").exists()


def test_fit_early_stop_and_threshold_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seq_len = 4
    model = _make_tiny_model(seq_len=seq_len)
    loader = _make_loaders(seq_len=seq_len)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.0)

    monkeypatch.setattr(
        "ashare_lab.training.mtl_finetune.evaluate",
        lambda *_args, **_kwargs: {"loss": 0.0, "ic": 0.0, "ic_3d": 0.0, "ic_5d": 0.0, "ic_10d": 0.0},
    )

    out = fit(
        model,
        loader,
        loader,
        opt,
        loss_weights=(1.0, 1.0, 1.0),
        max_epochs=3,
        patience=1,
        model_dir=tmp_path / "models",
        log_dir=tmp_path / "logs",
        early_stopping_threshold=1.0,
    )
    assert out["epochs_ran"] >= 1
