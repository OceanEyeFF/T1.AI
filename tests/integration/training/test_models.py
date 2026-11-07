import math
from pathlib import Path

import torch

from ashare_lab.models.transformer import (
    EarlyStoppingIC,
    compute_mtl_loss,
    create_mtl_model,
    freeze_encoder_layers,
)


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
