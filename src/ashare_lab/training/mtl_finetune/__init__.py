"""MTL Transformer fine-tuning utilities.

This package hosts reusable training logic extracted from `scripts/train_mtl.py`
and incremental (warm-start) fine-tuning with training gating and atomic
checkpoint writes.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import yaml

from ashare_lab.evaluation.metrics import information_coefficient
from ashare_lab.models.transformer import EarlyStoppingIC, MTLTransformer, freeze_encoder_layers
from ashare_lab.trend_schema import PRIMARY_TREND_LABEL_COLS, PRIMARY_TREND_PRED_COLS, target_name_from_pred


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def as_float_tuple3(
    values: object, default: tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> tuple[float, float, float]:
    if isinstance(values, (list, tuple)) and len(values) == 3:
        try:
            return (float(values[0]), float(values[1]), float(values[2]))
        except Exception:  # pragma: no cover
            return default
    return default


def as_float(value: object, default: float) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return float(default)
    return float(default)


def as_int(value: object, default: int) -> int:
    if value is None:
        return int(default)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return int(default)
    return int(default)


def count_labeled_samples(labels: torch.Tensor) -> int:
    """Count samples that have at least one non-NaN label across primary trend heads."""
    num_heads = len(PRIMARY_TREND_LABEL_COLS)
    if labels.ndim != 2 or labels.size(1) != num_heads:
        raise ValueError(f"labels must have shape [N, {num_heads}]")
    all_nan = torch.isnan(labels).all(dim=1)
    return int((~all_nan).sum().item())


def train_one_epoch(
    model: MTLTransformer,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_weights: Iterable[float] | torch.Tensor,
) -> float:
    model.train()
    device = next(model.parameters()).device
    total_loss = 0.0
    for feats, labels in loader:
        feats, labels = feats.to(device), labels.to(device)
        optimizer.zero_grad()
        _, losses = model(feats, labels, loss_weights=loss_weights)
        losses["total"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += float(losses["total"].item())
    return total_loss / max(1, len(loader))


@torch.no_grad()
def evaluate(
    model: MTLTransformer,
    loader: DataLoader,
    loss_weights: Iterable[float] | torch.Tensor,
) -> dict[str, float]:
    model.eval()
    device = next(model.parameters()).device
    all_preds: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []
    total_loss = 0.0
    num_heads = len(PRIMARY_TREND_PRED_COLS)
    for feats, labels in loader:
        feats, labels = feats.to(device), labels.to(device)
        preds, losses = model(feats, labels, loss_weights=loss_weights)
        stacked_pred = torch.stack([preds[pred_col] for pred_col in PRIMARY_TREND_PRED_COLS], dim=1)
        all_preds.append(stacked_pred.cpu())
        all_labels.append(labels.cpu())
        total_loss += float(losses["total"].item())

    preds_arr = torch.cat(all_preds).numpy() if all_preds else np.zeros((0, num_heads), dtype=float)
    labels_arr = torch.cat(all_labels).numpy() if all_labels else np.zeros((0, num_heads), dtype=float)

    metrics = {"loss": float(total_loss / max(1, len(loader)))}
    head_ics: list[float] = []
    for idx, pred_col in enumerate(PRIMARY_TREND_PRED_COLS):
        target = target_name_from_pred(pred_col)
        ic_value = information_coefficient(preds_arr[:, idx], labels_arr[:, idx]) if preds_arr.size else 0.0
        metrics[f"ic_{target}"] = float(ic_value)
        head_ics.append(float(ic_value))

    metrics["ic"] = float(np.mean(head_ics)) if head_ics else 0.0
    return metrics


def save_checkpoint_atomic(path: Path, payload: Mapping[str, object]) -> None:
    """Atomically save a torch checkpoint to `path` (tmpfile + fsync + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(path.parent),
            prefix=f"{path.name}.tmp.",
        ) as tmp_f:
            tmp_path = tmp_f.name
            torch.save(dict(payload), tmp_f)
            tmp_f.flush()
            os.fsync(tmp_f.fileno())

        os.replace(tmp_path, path)

        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
        except OSError:  # pragma: no cover
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            except OSError:  # pragma: no cover
                pass
            finally:
                os.close(dir_fd)
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:  # pragma: no cover
                pass


def fit(
    model: MTLTransformer,
    train_loader: DataLoader,
    valid_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    *,
    loss_weights: tuple[float, float, float],
    max_epochs: int,
    patience: int,
    model_dir: Path,
    log_dir: Path,
    early_stopping_threshold: float | None = None,
) -> dict[str, object]:
    """Full training with early stopping and atomic checkpointing."""
    model_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    best_path = model_dir / "best_mtl.pt"
    latest_path = model_dir / "latest_mtl.pt"
    stopper = EarlyStoppingIC(patience=patience, min_delta=0.0)

    history: list[dict[str, float]] = []
    best_ic = -float("inf")

    for epoch in range(1, max_epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, loss_weights)
        val_metrics = evaluate(model, valid_loader, loss_weights)

        row = {
            "epoch": float(epoch),
            "train_loss": float(train_loss),
            "val_loss": float(val_metrics["loss"]),
            "val_ic": float(val_metrics["ic"]),
            "val_ic_3d": float(val_metrics["ic_3d"]),
            "val_ic_5d": float(val_metrics["ic_5d"]),
            "val_ic_10d": float(val_metrics["ic_10d"]),
        }
        history.append(row)

        print(
            f"Epoch {epoch}/{max_epochs} "
            f"train_loss={row['train_loss']:.6f} "
            f"val_loss={row['val_loss']:.6f} "
            f"val_ic={row['val_ic']:.4f}"
        )

        latest_payload = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": epoch,
            "train_loss": float(train_loss),
            "val_loss": float(val_metrics.get("loss", 0.0)),
            "val_ic": float(val_metrics.get("ic", 0.0)),
            "config": {"loss_weights": loss_weights},
            "mode": "full",
        }
        save_checkpoint_atomic(latest_path, latest_payload)

        ic = float(val_metrics["ic"])
        if ic > best_ic:
            best_ic = ic
            save_checkpoint_atomic(best_path, latest_payload)
            print(f"[checkpoint] Saved best model: {best_path} (val_ic={best_ic:.4f})")

        if stopper.step(ic):
            print(f"[early-stop] No val_ic improvement for {patience} epoch(s). Stop at epoch={epoch}.")
            break

    try:
        pd.DataFrame(history).to_csv(log_dir / "mtl_train_log.csv", index=False)
    except Exception:  # pragma: no cover
        pass

    if early_stopping_threshold is not None and best_ic < early_stopping_threshold:
        print(
            f"[warn] best val_ic={best_ic:.4f} < threshold={early_stopping_threshold:.4f}. "
            f"Consider revisiting features/hyperparams."
        )

    return {
        "history": history,
        "best_ic": float(best_ic),
        "best_path": str(best_path),
        "latest_path": str(latest_path),
        "epochs_ran": len(history),
    }


def _parse_yyyy_mm_dd(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD, got {value!r}") from exc


@dataclass(frozen=True)
class IncrementalTrainConfig:
    enabled: bool = True
    trigger_schedule: str = "weekly"  # weekly / daily / manual
    min_labeled_samples: int = 100
    freeze_layers: int = 2
    learning_rate: float = 5e-5
    weight_decay: float = 1e-5
    max_epochs: int = 3
    early_stopping_patience: int = 2
    warm_start_checkpoint: Path = Path("models/latest_mtl.pt")
    save_checkpoint: Path = Path("models/latest_mtl.pt")

    @classmethod
    def from_config_dict(cls, cfg: Mapping[str, object]) -> "IncrementalTrainConfig":
        inc = cfg.get("incremental_training", {}) if isinstance(cfg, Mapping) else {}
        if not isinstance(inc, Mapping):
            inc = {}

        enabled = bool(inc.get("enabled", True))
        schedule = str(inc.get("trigger_schedule", "weekly"))
        min_samples = as_int(inc.get("min_labeled_samples", 100), 100)
        freeze_k = as_int(inc.get("freeze_layers", 2), 2)
        lr = as_float(inc.get("learning_rate", 5e-5), 5e-5)
        wd = as_float(inc.get("weight_decay", 1e-5), 1e-5)
        max_epochs = as_int(inc.get("max_epochs", 3), 3)
        patience = as_int(inc.get("early_stopping_patience", 2), 2)
        warm = Path(str(inc.get("warm_start_checkpoint", "models/latest_mtl.pt")))
        save = Path(str(inc.get("save_checkpoint", "models/latest_mtl.pt")))

        return cls(
            enabled=enabled,
            trigger_schedule=schedule,
            min_labeled_samples=min_samples,
            freeze_layers=freeze_k,
            learning_rate=lr,
            weight_decay=wd,
            max_epochs=max_epochs,
            early_stopping_patience=patience,
            warm_start_checkpoint=warm,
            save_checkpoint=save,
        )


class TrainingGate:
    def should_train(
        self,
        current_date: str,
        last_train_date: str | None,
        schedule: str,
        labeled_count: int,
        min_samples: int,
    ) -> tuple[bool, str]:
        if labeled_count < int(min_samples):
            return False, f"labeled_count={labeled_count} < min_samples={min_samples}"

        schedule = str(schedule).lower().strip()
        if schedule == "manual":
            return False, "schedule=manual"

        cur = _parse_yyyy_mm_dd(current_date)
        if schedule == "daily":
            return True, "schedule=daily"

        if schedule == "weekly":
            if last_train_date is None:
                return True, "schedule=weekly (no previous train)"
            last = _parse_yyyy_mm_dd(last_train_date)
            days = (cur - last).days
            if days >= 7:
                return True, f"schedule=weekly (days_since_last={days})"
            return False, f"schedule=weekly (days_since_last={days} < 7)"

        return False, f"unknown schedule={schedule!r}"


def infer_last_train_date_from_checkpoint(ckpt: Mapping[str, object] | None) -> str | None:
    if not ckpt:
        return None
    trained_at = ckpt.get("trained_at")
    if isinstance(trained_at, str) and trained_at:
        return trained_at
    return None


class IncrementalTrainer:
    def __init__(
        self,
        config: IncrementalTrainConfig,
        model: MTLTransformer,
        train_loader: DataLoader,
        val_loader: DataLoader,
        *,
        loss_weights: tuple[float, float, float] | None = None,
    ):
        self.config = config
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.loss_weights = (
            loss_weights if loss_weights is not None else tuple(float(x) for x in model.config.loss_weights)
        )

    def load_warm_start_checkpoint(self) -> Mapping[str, object] | None:
        path = self.config.warm_start_checkpoint
        if not path.exists():
            return None
        device = next(self.model.parameters()).device
        try:
            return torch.load(path, map_location=device, weights_only=False)
        except Exception as exc:
            raise ValueError(f"failed to load warm-start checkpoint: {path}") from exc

    def freeze_encoder_layers(self, num_layers: int) -> None:
        freeze_encoder_layers(self.model, num_layers)

    def validate(self) -> dict[str, float]:
        return evaluate(self.model, self.val_loader, self.loss_weights)

    def save_checkpoint_atomic(
        self,
        path: Path,
        optimizer: torch.optim.Optimizer,
        epoch: int,
        train_loss: float,
        val_metrics: Mapping[str, float],
        *,
        current_date: str,
        trigger_reason: str,
        labeled_count: int,
    ) -> None:
        payload = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": int(epoch),
            "train_loss": float(train_loss),
            "val_loss": float(val_metrics.get("loss", 0.0)),
            "val_ic": float(val_metrics.get("ic", 0.0)),
            "trained_at": str(current_date),
            "trigger_reason": str(trigger_reason),
            "labeled_count": int(labeled_count),
            "mode": "incremental",
            "config": {
                "loss_weights": self.loss_weights,
                "learning_rate": float(self.config.learning_rate),
                "freeze_layers": int(self.config.freeze_layers),
                "max_epochs": int(self.config.max_epochs),
                "early_stopping_patience": int(self.config.early_stopping_patience),
            },
        }
        save_checkpoint_atomic(path, payload)

    def run(
        self,
        gate: TrainingGate,
        current_date: str,
        last_train_date: str | None,
        labeled_count: int,
    ) -> dict[str, object]:
        if not self.config.enabled:
            return {"skipped": True, "reason": "incremental_training.disabled"}

        should, reason = gate.should_train(
            current_date=current_date,
            last_train_date=last_train_date,
            schedule=self.config.trigger_schedule,
            labeled_count=int(labeled_count),
            min_samples=int(self.config.min_labeled_samples),
        )
        if not should:
            return {"skipped": True, "reason": reason}

        ckpt = self.load_warm_start_checkpoint()
        if ckpt is not None and "model_state_dict" in ckpt:
            self.model.load_state_dict(ckpt["model_state_dict"])  # type: ignore[arg-type]

        if self.config.freeze_layers > 0:
            self.freeze_encoder_layers(self.config.freeze_layers)

        optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.model.parameters()),
            lr=float(self.config.learning_rate),
            weight_decay=float(self.config.weight_decay),
        )

        stopper = EarlyStoppingIC(patience=int(self.config.early_stopping_patience), min_delta=0.0)
        best_ic = -float("inf")
        best_epoch = 0
        best_state: dict[str, torch.Tensor] | None = None
        latest_metrics: dict[str, float] = {}
        latest_train_loss = float("inf")

        for epoch in range(1, int(self.config.max_epochs) + 1):
            latest_train_loss = float(train_one_epoch(self.model, self.train_loader, optimizer, self.loss_weights))
            latest_metrics = self.validate()
            ic = float(latest_metrics.get("ic", 0.0))
            if ic > best_ic:
                best_ic = ic
                best_epoch = epoch
                best_state = {k: v.detach().clone() for k, v in self.model.state_dict().items()}
            if stopper.step(ic):
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)

        save_path = self.config.save_checkpoint
        self.save_checkpoint_atomic(
            save_path,
            optimizer=optimizer,
            epoch=best_epoch if best_epoch else int(self.config.max_epochs),
            train_loss=latest_train_loss,
            val_metrics=latest_metrics,
            current_date=current_date,
            trigger_reason=reason,
            labeled_count=int(labeled_count),
        )

        return {
            "skipped": False,
            "reason": reason,
            "epochs": int(best_epoch if best_epoch else int(self.config.max_epochs)),
            "best_val_ic": float(best_ic),
            "val_ic": float(latest_metrics.get("ic", 0.0)),
            "train_loss": float(latest_train_loss),
            "checkpoint": str(save_path),
            "learning_rate": float(self.config.learning_rate),
            "freeze_layers": int(self.config.freeze_layers),
        }


__all__ = [
    "IncrementalTrainConfig",
    "IncrementalTrainer",
    "TrainingGate",
    "as_float",
    "as_float_tuple3",
    "as_int",
    "count_labeled_samples",
    "evaluate",
    "fit",
    "infer_last_train_date_from_checkpoint",
    "load_yaml",
    "save_checkpoint_atomic",
    "train_one_epoch",
]
