import sys
from pathlib import Path

import pytest
import torch


from scripts.run_lstm_rolling_retrain_dim19_regime import _compute_head_loss


def test_l1_loss_mode_matches_abs_error_mean() -> None:
    pred = torch.tensor([0.1, -0.2, 0.3], dtype=torch.float32)
    target = torch.tensor([0.0, -0.1, 0.1], dtype=torch.float32)
    total, parts = _compute_head_loss(pred, target, loss_type="l1", loss_alpha=0.3, ic_rank_beta=0.5)
    expected = torch.mean(torch.abs(pred - target))
    assert float(total) == pytest.approx(float(expected), abs=1e-6)
    assert "rank_loss" in parts
    assert "ic_loss" in parts


def test_rank_aware_loss_backpropagates() -> None:
    pred = torch.tensor([0.1, -0.2, 0.4, -0.3], dtype=torch.float32, requires_grad=True)
    target = torch.tensor([0.3, -0.1, 0.2, -0.4], dtype=torch.float32)
    total, _ = _compute_head_loss(pred, target, loss_type="rank_aware", loss_alpha=0.2, ic_rank_beta=0.5)
    total.backward()
    assert pred.grad is not None
    assert torch.isfinite(pred.grad).all()


def test_ic_rank_aware_prefers_aligned_prediction() -> None:
    target = torch.tensor([0.5, 0.2, -0.1, -0.4], dtype=torch.float32)
    aligned = torch.tensor([0.4, 0.1, -0.2, -0.3], dtype=torch.float32)
    reversed_pred = -aligned

    loss_aligned, _ = _compute_head_loss(
        aligned, target, loss_type="ic_rank_aware", loss_alpha=0.2, ic_rank_beta=0.5
    )
    loss_reversed, _ = _compute_head_loss(
        reversed_pred, target, loss_type="ic_rank_aware", loss_alpha=0.2, ic_rank_beta=0.5
    )

    assert float(loss_aligned) < float(loss_reversed)
