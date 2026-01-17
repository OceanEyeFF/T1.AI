#!/usr/bin/env python
"""多任务Transformer训练脚本

特点：
- 支持warm-start：自动加载最新checkpoint
- 可选冻结前K个encoder层
- 基于验证集IC的早停（连续5轮无提升停止）
- 配置化超参，YAML文件与命令行可同时覆盖

数据集格式（Parquet，task-1/build_sequence_dataset.py产出）：
  - 必须包含三列标签：label_3d, label_5d, label_10d（允许 NaN）
  - 特征列采用展开序列格式：{feature_name}_t{0..seq_len-1}
  - 可选包含 meta 列：date, symbol, mask（不参与训练）

示例：
    python scripts/train_mtl.py --config configs/model_mtl.yaml
    python scripts/train_mtl.py --config configs/model_mtl.yaml --dry-run
"""

from __future__ import annotations

import argparse
import glob
import math
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import yaml

from ashare_lab.evaluation.metrics import information_coefficient
from ashare_lab.models.transformer import (
    EarlyStoppingIC,
    MTLTransformer,
    compute_mtl_loss,
    create_mtl_model,
    freeze_encoder_layers,
)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _latest_checkpoint(save_dir: Path) -> Path | None:
    ckpts = sorted(glob.glob(str(save_dir / "*.pt")), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    return Path(ckpts[0]) if ckpts else None


def _as_float_tuple3(values: object, default: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> tuple[float, float, float]:
    if isinstance(values, (list, tuple)) and len(values) == 3:
        try:
            return (float(values[0]), float(values[1]), float(values[2]))
        except Exception:  # pragma: no cover
            return default
    return default


def _as_float(value: object, default: float) -> float:
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


def _as_int(value: object, default: int) -> int:
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


def _synthetic_dataset(
    num_samples: int,
    seq_len: int,
    input_dim: int,
    nan_ratio: float = 0.1,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """生成合成特征和标签，方便dry-run与单元测试。"""
    features = torch.randn(num_samples, seq_len, input_dim)
    labels = torch.randn(num_samples, 3)
    if nan_ratio > 0:
        mask = torch.rand_like(labels).lt(nan_ratio)
        labels = labels.masked_fill(mask, float("nan"))
    return features, labels


def _infer_label_columns(df: pd.DataFrame) -> list[str]:
    cols: list[tuple[int, str]] = []
    for c in df.columns:
        if isinstance(c, str) and c.startswith("label_") and c.endswith("d"):
            mid = c[len("label_") : -1]
            if mid.isdigit():
                cols.append((int(mid), c))
    cols = sorted(cols, key=lambda x: x[0])
    return [c for _, c in cols]


def _infer_feature_bases(df: pd.DataFrame, seq_len: int) -> list[str]:
    # Expect flattened columns: {base}_t{t}. Find bases that have t0..t{seq_len-1}.
    bases: set[str] = set()
    for c in df.columns:
        if not isinstance(c, str):
            continue
        if c.endswith("_t0"):
            bases.add(c[: -len("_t0")])

    out: list[str] = []
    for base in sorted(bases):
        ok = True
        for t in range(seq_len):
            if f"{base}_t{t}" not in df.columns:
                ok = False
                break
        if ok:
            out.append(base)
    return out


def _infer_seq_len(df: pd.DataFrame) -> int | None:
    # Look for suffix _t{n}; return max+1.
    max_t: int | None = None
    for c in df.columns:
        if not isinstance(c, str):
            continue
        if "_t" not in c:
            continue
        try:
            t_str = c.rsplit("_t", 1)[1]
        except Exception:
            continue
        if not t_str.isdigit():
            continue
        t = int(t_str)
        if max_t is None or t > max_t:
            max_t = t
    return None if max_t is None else (max_t + 1)


def load_sequence_parquet(path: Path, seq_len: int | None = None) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """Load a flattened sequence dataset split from parquet.

    Returns:
        X: [N, seq_len, n_feat] float32
        y: [N, 3] float32 (NaNs preserved)
        info: dict with inferred columns and shapes
    """
    df = pd.read_parquet(path)
    inferred_len = _infer_seq_len(df)
    if seq_len is None:
        if inferred_len is None:
            raise ValueError(f"cannot infer seq_len from columns in {path}")
        seq_len = inferred_len
    else:
        if inferred_len is not None and inferred_len != seq_len:
            raise ValueError(f"seq_len mismatch: config={seq_len}, data={inferred_len} ({path})")

    label_cols = _infer_label_columns(df)
    if label_cols[:3] != ["label_3d", "label_5d", "label_10d"]:
        # tolerate additional labels, but require these 3 to exist
        required = {"label_3d", "label_5d", "label_10d"}
        if not required.issubset(set(label_cols)):
            raise ValueError(f"parquet must contain labels {sorted(required)}; got {label_cols}")
        label_cols = ["label_3d", "label_5d", "label_10d"]

    bases = _infer_feature_bases(df, seq_len)
    if not bases:
        raise ValueError(f"no flattened feature columns like '*_t0' found in {path}")

    feature_cols = [f"{base}_t{t}" for t in range(seq_len) for base in bases]
    X_flat = df[feature_cols].to_numpy(dtype=np.float32, copy=False)
    X = X_flat.reshape(X_flat.shape[0], seq_len, len(bases))
    y = df[label_cols].to_numpy(dtype=np.float32, copy=False)

    return (
        torch.from_numpy(X),
        torch.from_numpy(y),
        {"seq_len": seq_len, "input_dim": len(bases), "feature_bases": bases, "label_cols": label_cols},
    )


def build_dataloaders_from_parquet(
    dataset_dir: Path,
    batch_size: int,
    seq_len: int,
) -> tuple[DataLoader, DataLoader, DataLoader, dict]:
    train_path = dataset_dir / "train.parquet"
    valid_path = dataset_dir / "valid.parquet"
    test_path = dataset_dir / "test.parquet"
    for p in [train_path, valid_path, test_path]:
        if not p.exists():
            raise FileNotFoundError(f"missing dataset split: {p}")

    X_train, y_train, info = load_sequence_parquet(train_path, seq_len=seq_len)
    X_valid, y_valid, _ = load_sequence_parquet(valid_path, seq_len=seq_len)
    X_test, y_test, _ = load_sequence_parquet(test_path, seq_len=seq_len)

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)
    valid_loader = DataLoader(TensorDataset(X_valid, y_valid), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size=batch_size, shuffle=False)
    return train_loader, valid_loader, test_loader, info


def build_dataloaders(
    batch_size: int,
    seq_len: int,
    input_dim: int,
    dry_run: bool,
    dataset_dir: Path | None,
) -> tuple[DataLoader, DataLoader, DataLoader, dict]:
    if dry_run:
        total = 128
        features, labels = _synthetic_dataset(total, seq_len, input_dim)
        split = math.floor(len(features) * 0.8)
        train_ds = TensorDataset(features[:split], labels[:split])
        valid_ds = TensorDataset(features[split:], labels[split:])
        test_ds = TensorDataset(features[split:], labels[split:])
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        valid_loader = DataLoader(valid_ds, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
        return train_loader, valid_loader, test_loader, {"seq_len": seq_len, "input_dim": input_dim}

    if dataset_dir is None:
        raise ValueError("dataset_dir is required when not in --dry-run mode")

    return build_dataloaders_from_parquet(dataset_dir, batch_size=batch_size, seq_len=seq_len)


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
    return total_loss / len(loader)


@torch.no_grad()
def evaluate(
    model: MTLTransformer,
    loader: DataLoader,
    loss_weights: Iterable[float] | torch.Tensor,
) -> dict:
    model.eval()
    device = next(model.parameters()).device
    all_preds = []
    all_labels = []
    total_loss = 0.0
    for feats, labels in loader:
        feats, labels = feats.to(device), labels.to(device)
        preds, losses = model(feats, labels, loss_weights=loss_weights)
        stacked_pred = torch.stack([preds["pred_3d"], preds["pred_5d"], preds["pred_10d"]], dim=1)
        all_preds.append(stacked_pred.cpu())
        all_labels.append(labels.cpu())
        total_loss += float(losses["total"].item())

    preds_arr = torch.cat(all_preds).numpy()
    labels_arr = torch.cat(all_labels).numpy()

    ic_3d = information_coefficient(preds_arr[:, 0], labels_arr[:, 0])
    ic_5d = information_coefficient(preds_arr[:, 1], labels_arr[:, 1])
    ic_10d = information_coefficient(preds_arr[:, 2], labels_arr[:, 2])
    ic = float(np.mean([ic_3d, ic_5d, ic_10d]))
    return {
        "loss": total_loss / max(1, len(loader)),
        "ic": ic,
        "ic_3d": ic_3d,
        "ic_5d": ic_5d,
        "ic_10d": ic_10d,
    }


def _save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    train_loss: float,
    val_metrics: dict,
    config: dict,
) -> None:
    payload = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "train_loss": float(train_loss),
        "val_loss": float(val_metrics.get("loss", 0.0)),
        "val_ic": float(val_metrics.get("ic", 0.0)),
        "config": config,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


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
) -> dict:
    """Train model with early stopping and checkpointing.

    Returns:
        dict with history, best_ic, best_path, latest_path, epochs_ran
    """
    model_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    best_path = model_dir / "best_mtl.pt"
    latest_path = model_dir / "latest_mtl.pt"
    stopper = EarlyStoppingIC(patience=patience, min_delta=0.0)

    history: list[dict] = []
    best_ic = -float("inf")

    for epoch in range(1, max_epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, loss_weights)
        val_metrics = evaluate(model, valid_loader, loss_weights)

        row = {
            "epoch": epoch,
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

        _save_checkpoint(latest_path, model, optimizer, epoch, train_loss, val_metrics, config={"loss_weights": loss_weights})

        ic = float(val_metrics["ic"])
        if ic > best_ic:
            best_ic = ic
            _save_checkpoint(best_path, model, optimizer, epoch, train_loss, val_metrics, config={"loss_weights": loss_weights})
            print(f"[checkpoint] Saved best model: {best_path} (val_ic={best_ic:.4f})")

        if stopper.step(ic):
            print(f"[early-stop] No val_ic improvement for {patience} epoch(s). Stop at epoch={epoch}.")
            break

    # Persist history
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
        "best_ic": best_ic,
        "best_path": str(best_path),
        "latest_path": str(latest_path),
        "epochs_ran": len(history),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MTL Transformer 训练脚本")
    parser.add_argument("--config", type=str, required=True, help="YAML配置文件路径")
    parser.add_argument("--dataset", type=str, default=None, help="数据集目录（默认: data/datasets）")
    parser.add_argument("--dry-run", action="store_true", help="使用合成数据快速验证流程")
    parser.add_argument("--max-epochs", type=int, default=None, help="覆盖配置中的最大epoch数")
    parser.add_argument("--freeze-layers", type=int, default=0, help="冻结前K个encoder层")
    parser.add_argument("--no-warm-start", action="store_true", help="禁用自动warm-start")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"], help="训练设备")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    cfg = _load_yaml(Path(args.config))
    model_cfg = cfg.get("model", {})
    train_cfg = cfg.get("training", {})
    data_cfg = cfg.get("data", {})
    output_cfg = cfg.get("output", {})

    loss_weights = _as_float_tuple3(model_cfg.get("loss_weights", None))

    model = create_mtl_model(
        input_dim=_as_int(model_cfg.get("input_dim", 6), 6),
        d_model=_as_int(model_cfg.get("d_model", 128), 128),
        n_layers=_as_int(model_cfg.get("n_layers", 4), 4),
        n_heads=_as_int(model_cfg.get("n_heads", 4), 4),
        d_ff=_as_int(model_cfg.get("d_ff", 512), 512),
        dropout=_as_float(model_cfg.get("dropout", 0.1), 0.1),
        max_seq_len=_as_int(model_cfg.get("max_seq_len", 512), 512),
        min_seq_len=_as_int(model_cfg.get("min_seq_len", 30), 30),
        loss_weights=loss_weights,
    )

    torch.manual_seed(int(args.seed))
    if args.device == "cuda":
        device = torch.device("cuda")
    elif args.device == "cpu":
        device = torch.device("cpu")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    if not args.no_warm_start:
        model_dir = Path(output_cfg.get("model_dir", "models"))
        ckpt = model_dir / "latest_mtl.pt"
        if ckpt.exists():
            try:
                state = torch.load(ckpt, map_location=device, weights_only=False)
                model.load_state_dict(state["model_state_dict"])
                print(f"[warm-start] Loaded checkpoint: {ckpt}")
            except Exception as exc:  # pragma: no cover - 容错处理
                print(f"[warm-start] Failed to load {ckpt}: {exc}. Continuing without warm-start.")

    if args.freeze_layers > 0:
        freeze_encoder_layers(model, args.freeze_layers)
        print(f"[freeze] Frozen first {args.freeze_layers} encoder layers")

    batch_size = train_cfg.get("batch_size", 32)
    lr = _as_float(train_cfg.get("learning_rate", train_cfg.get("lr", 1e-4)), 1e-4)
    weight_decay = _as_float(train_cfg.get("weight_decay", 1e-5), 1e-5)
    max_epochs = args.max_epochs or _as_int(train_cfg.get("max_epochs", train_cfg.get("epochs", 50)), 50)
    patience = _as_int(train_cfg.get("early_stopping_patience", 5), 5)
    threshold = train_cfg.get("early_stopping_threshold", None)

    if args.dry_run and args.max_epochs is None:
        max_epochs = 1

    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=weight_decay)

    seq_len = _as_int(data_cfg.get("seq_len", model.config.min_seq_len), model.config.min_seq_len)
    dataset_dir = Path(args.dataset or data_cfg.get("dataset_dir", "data/datasets"))

    metric = str(train_cfg.get("early_stopping_metric", "val_ic"))
    if metric != "val_ic":
        raise ValueError(f"unsupported early_stopping_metric: {metric} (only 'val_ic' is supported)")

    train_loader, valid_loader, _test_loader, data_info = build_dataloaders(
        batch_size=batch_size,
        seq_len=seq_len,
        input_dim=_as_int(model_cfg.get("input_dim", model.config.input_dim), model.config.input_dim),
        dry_run=args.dry_run,
        dataset_dir=dataset_dir,
    )

    inferred_input_dim = int(data_info.get("input_dim", model.config.input_dim))
    if inferred_input_dim != model.config.input_dim:
        print(
            f"[warn] model.input_dim={model.config.input_dim} but dataset input_dim={inferred_input_dim}; "
            f"consider updating configs/model_mtl.yaml"
        )

    model_dir = Path(output_cfg.get("model_dir", "models"))
    log_dir = Path(output_cfg.get("log_dir", "logs"))

    results = fit(
        model,
        train_loader,
        valid_loader,
        optimizer,
        loss_weights=loss_weights,
        max_epochs=int(max_epochs),
        patience=patience,
        model_dir=model_dir,
        log_dir=log_dir,
        early_stopping_threshold=_as_float(threshold, 0.0) if threshold is not None else None,
    )
    print(f"[done] best val_ic={results['best_ic']:.4f} best={results['best_path']} latest={results['latest_path']}")


if __name__ == "__main__":
    main()
