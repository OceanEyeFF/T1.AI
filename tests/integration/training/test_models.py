import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
import yaml

import sys

from ashare_lab.models.transformer import (
    EarlyStoppingIC,
    MTLTransformer,
    compute_mtl_loss,
    create_mtl_model,
    freeze_encoder_layers,
)


from scripts.train_mtl import build_dataloaders_from_parquet, fit  # noqa: E402

from ashare_lab.dataset.sequence_parquet import load_sequence_parquet


def _write_sequence_split(
    path: Path,
    *,
    n_samples: int,
    seq_len: int,
    input_dim: int,
    seed: int = 0,
    constant_labels: bool = False,
) -> None:
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n_samples, seq_len, input_dim)).astype(np.float32)

    if constant_labels:
        y = np.zeros((n_samples, 3), dtype=np.float32)
    else:
        # Make labels correlated with the last timestep to produce a learnable signal.
        last = X[:, -1, :]
        y3 = last[:, 0] + 0.01 * rng.normal(size=n_samples).astype(np.float32)
        y5 = last[:, 1 % input_dim] + 0.01 * rng.normal(size=n_samples).astype(np.float32)
        y10 = last[:, 2 % input_dim] + 0.01 * rng.normal(size=n_samples).astype(np.float32)
        y = np.stack([y3, y5, y10], axis=1).astype(np.float32)

    rows: dict[str, np.ndarray] = {
        "date": pd.date_range("2024-01-01", periods=n_samples, freq="D").astype(str).to_numpy(),
        "symbol": np.array(["000001"] * n_samples, dtype=object),
        "mask": np.ones(n_samples, dtype=bool),
        "label_3d": y[:, 0],
        "label_5d": y[:, 1],
        "label_10d": y[:, 2],
    }

    for t in range(seq_len):
        for j in range(input_dim):
            rows[f"feat{j}_t{t}"] = X[:, t, j]

    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _make_sequence_dataset_dir(
    tmp_path: Path,
    *,
    seq_len: int = 8,
    input_dim: int = 10,
    n_train: int = 128,
    n_valid: int = 64,
    n_test: int = 64,
    constant_valid_labels: bool = False,
) -> Path:
    d = tmp_path / "datasets"
    _write_sequence_split(d / "train.parquet", n_samples=n_train, seq_len=seq_len, input_dim=input_dim, seed=1)
    _write_sequence_split(
        d / "valid.parquet",
        n_samples=n_valid,
        seq_len=seq_len,
        input_dim=input_dim,
        seed=2,
        constant_labels=constant_valid_labels,
    )
    _write_sequence_split(d / "test.parquet", n_samples=n_test, seq_len=seq_len, input_dim=input_dim, seed=3)
    return d


def test_mtl_output_shapes():
    model = create_mtl_model(input_dim=6, d_model=64, n_layers=4, n_heads=4, d_ff=128, min_seq_len=30)
    x = torch.randn(4, 30, 6)
    preds = model(x)
    assert set(preds.keys()) == {"pred_3d", "pred_5d", "pred_10d"}
    for v in preds.values():
        assert v.shape == (4,)


def test_masked_loss_ignores_nan():
    preds = {
        "pred_3d": torch.tensor([1.0, 2.0]),
        "pred_5d": torch.tensor([0.5, -0.5]),
        "pred_10d": torch.tensor([1.0, 3.0]),
    }
    labels = torch.tensor(
        [
            [0.0, float("nan"), 2.0],
            [0.0, float("nan"), 2.0],
        ]
    )
    total, losses = compute_mtl_loss(preds, labels, (1, 1, 1))
    # 3d: mean(|1|,|2|)=1.5; 5d:全部NaN→0; 10d: mean(|-1|,|1|)=1
    assert math.isclose(losses["l1_3d"].item(), 1.5, rel_tol=1e-6)
    assert math.isclose(losses["l1_5d"].item(), 0.0, rel_tol=1e-6)
    assert math.isclose(losses["l1_10d"].item(), 1.0, rel_tol=1e-6)
    assert math.isclose(total.item(), 2.5, rel_tol=1e-6)


def test_weighted_loss_sum():
    preds = torch.zeros(1, 3)
    labels = torch.tensor([[1.0, 2.0, 3.0]])
    total, losses = compute_mtl_loss(
        {"pred_3d": preds[:, 0], "pred_5d": preds[:, 1], "pred_10d": preds[:, 2]},
        labels,
        (1.0, 2.0, 3.0),
    )
    assert math.isclose(losses["l1_3d"].item(), 1.0)
    assert math.isclose(losses["l1_5d"].item(), 2.0)
    assert math.isclose(losses["l1_10d"].item(), 3.0)
    assert math.isclose(total.item(), 14.0)  # 1*1 + 2*2 + 3*3


def test_min_seq_len_enforced():
    model = create_mtl_model(min_seq_len=30)
    x = torch.randn(2, 10, model.config.input_dim)
    try:
        model(x)
    except ValueError as exc:
        assert "sequence length" in str(exc)
    else:
        raise AssertionError("Expected ValueError for short sequence")


def test_freeze_encoder_layers():
    model = create_mtl_model(n_layers=5)
    freeze_encoder_layers(model, 2)
    enc_layers = list(model.transformer_encoder.layers)
    assert all(not any(p.requires_grad for p in layer.parameters()) for layer in enc_layers[:2])
    assert all(any(p.requires_grad for p in layer.parameters()) for layer in enc_layers[2:])


def test_warm_start_state_load(tmp_path: Path):
    model = create_mtl_model()
    for param in model.parameters():
        param.data.uniform_(-0.1, 0.1)
    ckpt = tmp_path / "ckpt.pt"
    torch.save({"model_state_dict": model.state_dict()}, ckpt)

    new_model = create_mtl_model()
    state = torch.load(ckpt, map_location="cpu")
    new_model.load_state_dict(state["model_state_dict"])

    for p_old, p_new in zip(model.parameters(), new_model.parameters()):
        assert torch.allclose(p_old, p_new)


def test_early_stopping_ic_trigger():
    stopper = EarlyStoppingIC(patience=2, min_delta=0.0)
    ic_values = [0.1, 0.1, 0.1, 0.1]
    triggered = False
    for ic in ic_values:
        if stopper.step(ic):
            triggered = True
            break
    assert triggered


def test_all_nan_head_yields_zero_loss():
    preds = {
        "pred_3d": torch.tensor([0.0, 0.0]),
        "pred_5d": torch.tensor([0.0, 0.0]),
        "pred_10d": torch.tensor([1.0, -1.0]),
    }
    labels = torch.tensor(
        [
            [float("nan"), float("nan"), 1.0],
            [float("nan"), float("nan"), -1.0],
        ]
    )
    total, losses = compute_mtl_loss(preds, labels, (1, 1, 1))
    assert math.isclose(losses["l1_3d"].item(), 0.0)
    assert math.isclose(losses["l1_5d"].item(), 0.0)
    # 10d: |1-1| + |-1+1| -> 0
    assert math.isclose(losses["l1_10d"].item(), 0.0)
    assert math.isclose(total.item(), 0.0)


def test_compute_loss_raises_on_label_shape():
    preds = {"pred_3d": torch.randn(2), "pred_5d": torch.randn(2), "pred_10d": torch.randn(2)}
    labels = torch.randn(2, 2)  # wrong second dimension
    try:
        compute_mtl_loss(preds, labels, (1, 1, 1))
    except ValueError as exc:
        assert "labels must have shape" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid label shape")


def test_compute_loss_raises_on_head_count():
    preds_seq = [torch.randn(2), torch.randn(2)]  # only two heads
    labels = torch.randn(2, 3)
    try:
        compute_mtl_loss(preds_seq, labels, (1, 1, 1))
    except ValueError as exc:
        assert "three heads" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing heads")


def test_compute_loss_raises_on_weight_length():
    preds = {"pred_3d": torch.randn(2), "pred_5d": torch.randn(2), "pred_10d": torch.randn(2)}
    labels = torch.randn(2, 3)
    try:
        compute_mtl_loss(preds, labels, (1, 2))  # only two weights
    except ValueError as exc:
        assert "three elements" in str(exc)
    else:
        raise AssertionError("Expected ValueError for weight length")


def test_compute_loss_raises_on_pred_shape_mismatch():
    preds = {
        "pred_3d": torch.randn(3),  # length 3
        "pred_5d": torch.randn(2),
        "pred_10d": torch.randn(2),
    }
    labels = torch.randn(2, 3)
    try:
        compute_mtl_loss(preds, labels, (1, 1, 1))
    except ValueError as exc:
        assert "prediction and target shape" in str(exc)
    else:
        raise AssertionError("Expected ValueError for shape mismatch")


def test_model_init_validates_layer_and_seq_bounds():
    try:
        create_mtl_model(n_layers=7)
    except ValueError as exc:
        assert "n_layers" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid n_layers")

    try:
        create_mtl_model(max_seq_len=10, min_seq_len=30)
    except ValueError as exc:
        assert "max_seq_len" in str(exc)
    else:
        raise AssertionError("Expected ValueError for max_seq_len < min_seq_len")


def test_forward_raises_on_wrong_input_dim():
    model = create_mtl_model()
    bad_x = torch.randn(2, 30)  # missing feature dimension
    try:
        model(bad_x)
    except ValueError as exc:
        assert "input tensor must be 3D" in str(exc)
    else:
        raise AssertionError("Expected ValueError for wrong input ndim")


def test_train_mtl_loads_parquet_sequence_dataset(tmp_path: Path):
    dataset_dir = _make_sequence_dataset_dir(tmp_path, seq_len=6, input_dim=10, n_train=20, n_valid=10, n_test=10)
    X, y, info = load_sequence_parquet(dataset_dir / "train.parquet", seq_len=6)
    assert X.shape == (20, 6, 10)
    assert y.shape == (20, 3)
    assert info["seq_len"] == 6
    assert info["input_dim"] == 10

    # seq_len can be inferred from column suffixes.
    X2, y2, info2 = load_sequence_parquet(dataset_dir / "train.parquet")
    assert X2.shape == (20, 6, 10)
    assert y2.shape == (20, 3)
    assert info2["seq_len"] == 6
    assert info2["input_dim"] == 10

    # seq_len mismatch should be rejected.
    with pytest.raises(ValueError, match="seq_len mismatch"):
        _X_bad, _y_bad, _info_bad = load_sequence_parquet(dataset_dir / "train.parquet", seq_len=5)

    # Additional label columns are tolerated but the 3 required labels are used.
    df = pd.read_parquet(dataset_dir / "train.parquet")
    df["label_1d"] = 0.0
    df["junk_tX"] = 0.0  # cover non-digit suffix handling in seq_len inference
    extra_path = dataset_dir / "train_extra_labels.parquet"
    df.to_parquet(extra_path, index=False)
    _X3, _y3, info3 = load_sequence_parquet(extra_path, seq_len=6)
    assert info3["label_cols"] == ["label_3d", "label_5d", "label_10d"]

    # Missing required labels should raise.
    df_missing = df.drop(columns=["label_5d"])
    missing_path = dataset_dir / "train_missing_label.parquet"
    df_missing.to_parquet(missing_path, index=False)
    with pytest.raises(ValueError, match="parquet must contain labels"):
        _X_bad2, _y_bad2, _info_bad2 = load_sequence_parquet(missing_path, seq_len=6)

    # No flattened feature columns should raise.
    df_no_feat = pd.DataFrame(
        {
            "label_3d": np.zeros(4, dtype=np.float32),
            "label_5d": np.zeros(4, dtype=np.float32),
            "label_10d": np.zeros(4, dtype=np.float32),
        }
    )
    no_feat_path = dataset_dir / "train_no_features.parquet"
    df_no_feat.to_parquet(no_feat_path, index=False)
    with pytest.raises(ValueError, match="cannot infer seq_len"):
        _X_no_len, _y_no_len, _info_no_len = load_sequence_parquet(no_feat_path)
    with pytest.raises(ValueError, match="no flattened feature columns"):
        _X_bad3, _y_bad3, _info_bad3 = load_sequence_parquet(no_feat_path, seq_len=6)

    # Incomplete bases (has *_t0 but missing later timesteps) should be ignored.
    df_partial = pd.DataFrame(
        {
            "label_3d": np.zeros(3, dtype=np.float32),
            "label_5d": np.zeros(3, dtype=np.float32),
            "label_10d": np.zeros(3, dtype=np.float32),
            "bar_t0": np.ones(3, dtype=np.float32),
            "bar_t1": np.ones(3, dtype=np.float32),
            "foo_t0": np.ones(3, dtype=np.float32),
        }
    )
    partial_path = dataset_dir / "train_partial_bases.parquet"
    df_partial.to_parquet(partial_path, index=False)
    X4, _y4, info4 = load_sequence_parquet(partial_path, seq_len=2)
    assert X4.shape == (3, 2, 1)
    assert info4["feature_bases"] == ["bar"]


def test_train_loop_updates_params_and_saves_checkpoints(tmp_path: Path):
    dataset_dir = _make_sequence_dataset_dir(tmp_path, seq_len=8, input_dim=10, n_train=128, n_valid=64, n_test=64)
    train_loader, valid_loader, _test_loader, _info = build_dataloaders_from_parquet(
        dataset_dir, batch_size=32, seq_len=8
    )

    model = create_mtl_model(
        input_dim=10,
        d_model=32,
        n_layers=4,
        n_heads=4,
        d_ff=64,
        dropout=0.1,
        max_seq_len=16,
        min_seq_len=8,
        loss_weights=(1.0, 1.0, 1.0),
    ).to(torch.device("cpu"))

    before = {k: v.detach().clone() for k, v in model.state_dict().items()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)

    out = fit(
        model,
        train_loader,
        valid_loader,
        optimizer,
        loss_weights=(1.0, 1.0, 1.0),
        max_epochs=4,
        patience=10,
        model_dir=tmp_path / "models",
        log_dir=tmp_path / "logs",
    )

    assert (tmp_path / "models" / "best_mtl.pt").exists()
    assert (tmp_path / "models" / "latest_mtl.pt").exists()

    # Ensure at least one parameter changed (gradient update happened).
    after = model.state_dict()
    changed = any(not torch.allclose(before[k], after[k]) for k in before.keys())
    assert changed

    # Loss should be finite and generally decrease on this learnable synthetic dataset.
    history = out["history"]
    assert len(history) >= 2
    assert math.isfinite(history[0]["train_loss"])
    train_losses = [row["train_loss"] for row in history]
    assert min(train_losses[1:]) <= train_losses[0] + 1e-6

    ckpt = torch.load(tmp_path / "models" / "best_mtl.pt", map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt
    assert "val_ic" in ckpt


def test_early_stopping_triggers_when_val_ic_stalls(tmp_path: Path):
    dataset_dir = _make_sequence_dataset_dir(
        tmp_path,
        seq_len=8,
        input_dim=10,
        n_train=64,
        n_valid=64,
        n_test=64,
        constant_valid_labels=True,  # val labels constant -> IC always 0
    )
    train_loader, valid_loader, _test_loader, _info = build_dataloaders_from_parquet(
        dataset_dir, batch_size=32, seq_len=8
    )
    model = create_mtl_model(
        input_dim=10,
        d_model=32,
        n_layers=4,
        n_heads=4,
        d_ff=64,
        dropout=0.1,
        max_seq_len=16,
        min_seq_len=8,
        loss_weights=(1.0, 1.0, 1.0),
    ).to(torch.device("cpu"))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)

    out = fit(
        model,
        train_loader,
        valid_loader,
        optimizer,
        loss_weights=(1.0, 1.0, 1.0),
        max_epochs=20,
        patience=2,
        model_dir=tmp_path / "models",
        log_dir=tmp_path / "logs",
    )
    assert out["epochs_ran"] == 3  # first epoch sets best, then 2 stalls -> stop


def test_model_mtl_yaml_parses():
    cfg = yaml.safe_load(Path("inputs/configs/profiles/model_mtl.toml").read_text(encoding="utf-8"))
    assert isinstance(cfg, dict)
    assert cfg["model"]["input_dim"] == 11
    assert cfg["model"]["min_seq_len"] == 20
    assert cfg["data"]["seq_len"] == 20
    assert cfg["training"]["batch_size"] == 64
    assert float(cfg["training"]["learning_rate"]) == 1e-5
    assert float(cfg["training"]["weight_decay"]) == 1e-4
    assert cfg["training"]["early_stopping_patience"] == 8
    assert cfg["training"]["early_stopping_metric"] == "val_ic"


def test_train_mtl_runs_on_cuda_if_available(tmp_path: Path):
    if not torch.cuda.is_available():
        return
    try:
        torch.empty(1, device="cuda") + 1
    except RuntimeError:
        return

    dataset_dir = _make_sequence_dataset_dir(tmp_path, seq_len=8, input_dim=10, n_train=64, n_valid=64, n_test=64)
    train_loader, valid_loader, _test_loader, _info = build_dataloaders_from_parquet(
        dataset_dir, batch_size=32, seq_len=8
    )
    device = torch.device("cuda")
    model = create_mtl_model(
        input_dim=10,
        d_model=32,
        n_layers=4,
        n_heads=4,
        d_ff=64,
        dropout=0.1,
        max_seq_len=16,
        min_seq_len=8,
        loss_weights=(1.0, 1.0, 1.0),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
    out = fit(
        model,
        train_loader,
        valid_loader,
        optimizer,
        loss_weights=(1.0, 1.0, 1.0),
        max_epochs=1,
        patience=5,
        model_dir=tmp_path / "models",
        log_dir=tmp_path / "logs",
    )
    assert out["epochs_ran"] == 1
