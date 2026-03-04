#!/usr/bin/env python3
"""Run grouped ablation experiments for the dim52 no-hist-hl baseline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


BASELINE_FEATURE_GROUPS: dict[str, list[str]] = {
    "price_tech_core": [
        "return_1d",
        "return_5d",
        "return_10d",
        "return_20d",
        "return_60d",
        "volume_ratio_5d",
        "amount_change",
        "rsi_14",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "bollinger_deviation",
        "price_slope_5d",
        "price_slope_20d",
    ],
    "turnover_volume_micro": [
        "turnover_rate",
        "turnover_rate_f",
        "turnover_spread",
        "turnover_rate_z20",
        "db_volume_ratio",
        "db_volume_ratio_z20",
    ],
    "valuation_size": [
        "pe_ttm_z20",
        "pb_z20",
        "ps_ttm_z20",
        "dv_ttm",
        "total_mv_log",
        "circ_mv_log",
        "float_share_ratio",
    ],
    "moneyflow_structure": [
        "mf_net_amount_ratio",
        "mf_net_amount_abs_ratio",
        "mf_md_amount_ratio",
        "mf_lg_amount_ratio",
        "mf_elg_amount_ratio",
        "mf_buy_pressure_amount",
        "mf_buy_pressure_vol",
        "mf_flow_concentration",
        "mf_net_amount_z20",
        "mf_net_amount_impulse",
        "mf_large_amount_ratio",
        "mf_retail_amount_ratio",
        "mf_large_retail_spread",
    ],
    "moneyflow_momentum": [
        "mf_net_amount_ratio_ma5",
        "mf_net_amount_ratio_ma10",
        "mf_net_amount_ratio_mom5",
        "mf_net_amount_ratio_mom10",
        "mf_large_amount_ratio_ma5",
        "mf_large_amount_ratio_mom5",
        "mf_retail_amount_ratio_ma5",
        "mf_buy_pressure_amount_ma5",
        "mf_activity_ratio_20d",
    ],
    "market_state": [
        "market_mom_5d",
        "market_vol_20d",
        "market_amount_z20",
    ],
}

MONEYFLOW_MOMENTUM_FEATURES = list(BASELINE_FEATURE_GROUPS["moneyflow_momentum"])

MFM_SINGLE_FEATURE_GROUPS: dict[str, list[str]] = {
    feature: [feature] for feature in MONEYFLOW_MOMENTUM_FEATURES
}

MFM_SUBGROUP_FEATURES: dict[str, list[str]] = {
    "mfm_net_amount_ratio_trend": [
        "mf_net_amount_ratio_ma5",
        "mf_net_amount_ratio_ma10",
        "mf_net_amount_ratio_mom5",
        "mf_net_amount_ratio_mom10",
    ],
    "mfm_large_retail_trend": [
        "mf_large_amount_ratio_ma5",
        "mf_large_amount_ratio_mom5",
        "mf_retail_amount_ratio_ma5",
    ],
    "mfm_pressure_activity": [
        "mf_buy_pressure_amount_ma5",
        "mf_activity_ratio_20d",
    ],
}

GROUP_SETS: dict[str, dict[str, list[str]]] = {
    "base52": BASELINE_FEATURE_GROUPS,
    "mfm_single": MFM_SINGLE_FEATURE_GROUPS,
    "mfm_subgroup": MFM_SUBGROUP_FEATURES,
}

GROUP_SET_REQUIRE_FULL_COVERAGE: dict[str, bool] = {
    "base52": True,
    "mfm_single": False,
    "mfm_subgroup": False,
}


@dataclass(frozen=True)
class TrainArgs:
    seq_len: int
    train_window_months: int
    valid_window_months: int
    calibration_months: int
    sign_threshold: float
    hidden_size: int
    num_layers: int
    dropout: float
    lr: float
    batch_size: int
    max_epochs: int
    patience: int
    w3: float
    w5: float
    w10: float
    loss_type: str
    loss_alpha: float
    ic_rank_beta: float
    seed: int


def _run(cmd: list[str]) -> None:
    print("[cmd]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _infer_feature_bases(train_path: Path, seq_len: int) -> list[str]:
    df = pd.read_parquet(train_path)
    out: list[str] = []
    seen: set[str] = set()
    for col in df.columns:
        if not col.endswith("_t0"):
            continue
        base = col[:-3]
        if not base or base in seen:
            continue
        req = [f"{base}_t{i}" for i in range(seq_len)]
        if all(c in df.columns for c in req):
            out.append(base)
            seen.add(base)
    if not out:
        raise RuntimeError(f"no feature bases inferred from {train_path}")
    return out


def _validate_groups(
    feature_bases: list[str],
    selected_groups: list[str],
    group_map: dict[str, list[str]],
    *,
    require_full_coverage: bool,
) -> None:
    all_group_features: list[str] = []
    for g in selected_groups:
        all_group_features.extend(group_map[g])

    feature_set = set(feature_bases)
    group_set = set(all_group_features)

    dupes = sorted({x for x in all_group_features if all_group_features.count(x) > 1})
    missing = sorted(feature_set - group_set) if require_full_coverage else []
    extras = sorted(group_set - feature_set)

    if dupes:
        raise ValueError(f"group overlap features found: {dupes}")
    if missing:
        raise ValueError(f"features missing in group definitions: {missing}")
    if extras:
        raise ValueError(f"undefined features not in dataset: {extras}")


def _drop_group_dataset(base_dataset_dir: Path, out_dir: Path, drop_features: list[str], seq_len: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for split in ("train", "valid", "test"):
        src = base_dataset_dir / f"{split}.parquet"
        dst = out_dir / f"{split}.parquet"
        df = pd.read_parquet(src)
        drop_cols = [f"{f}_t{i}" for f in drop_features for i in range(seq_len)]
        keep_cols = [c for c in df.columns if c not in set(drop_cols)]
        df = df[keep_cols].copy()
        df.to_parquet(dst, index=False)
        print(f"[dataset] {split}: rows={len(df)} cols={len(df.columns)} -> {dst}")


def _run_train_for_group(dataset_dir: Path, report_path: Path, oos_path: Path, cfg: TrainArgs) -> None:
    cmd = [
        sys.executable,
        "scripts/run_lstm_rolling_retrain_dim19_regime.py",
        "--dataset-dir",
        str(dataset_dir),
        "--feature-mode",
        "auto",
        "--seq-len",
        str(cfg.seq_len),
        "--train-window-months",
        str(cfg.train_window_months),
        "--valid-window-months",
        str(cfg.valid_window_months),
        "--calibration-months",
        str(cfg.calibration_months),
        "--sign-threshold",
        str(cfg.sign_threshold),
        "--hidden-size",
        str(cfg.hidden_size),
        "--num-layers",
        str(cfg.num_layers),
        "--dropout",
        str(cfg.dropout),
        "--lr",
        str(cfg.lr),
        "--batch-size",
        str(cfg.batch_size),
        "--max-epochs",
        str(cfg.max_epochs),
        "--patience",
        str(cfg.patience),
        "--w3",
        str(cfg.w3),
        "--w5",
        str(cfg.w5),
        "--w10",
        str(cfg.w10),
        "--loss-type",
        str(cfg.loss_type),
        "--loss-alpha",
        str(cfg.loss_alpha),
        "--ic-rank-beta",
        str(cfg.ic_rank_beta),
        "--seed",
        str(cfg.seed),
        "--save-oos-parquet",
        str(oos_path),
        "--report",
        str(report_path),
    ]
    _run(cmd)


def _run_compare(reports: list[Path], tag: str, output_dir: Path, compare_prefix: str) -> None:
    report_args = [str(p) for p in reports]

    _run(
        [
            sys.executable,
            "scripts/audit_ic_reports.py",
            "--reports",
            *report_args,
            "--output-dir",
            str(output_dir),
            "--tag",
            f"{compare_prefix}_{tag}_coverage",
        ]
    )

    for metric_source, monthly_source, suffix in (
        ("raw", "raw", "raw"),
        ("calibrated", "calibrated", "cal"),
    ):
        _run(
            [
                sys.executable,
                "scripts/compare_ic_reports.py",
                "--reports",
                *report_args,
                "--metric-source",
                metric_source,
                "--monthly-source",
                monthly_source,
                "--daily-cs-mode",
                "required",
                "--output-dir",
                str(output_dir),
                "--tag",
                f"{compare_prefix}_{suffix}_{tag}",
            ]
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run grouped ablation on dim52 baseline.")
    parser.add_argument(
        "--group-set",
        choices=sorted(GROUP_SETS.keys()),
        default="base52",
        help="base52: 六大类消融；mfm_single: 资金流动量组单特征消融；mfm_subgroup: 资金流动量子组消融",
    )
    parser.add_argument(
        "--base-dataset-dir",
        default="data/datasets/lstm_quick8_52d_no_hist_hl_20230101_20260120_ts",
    )
    parser.add_argument(
        "--baseline-report",
        default="output/reports/lstm_dim52_no_hist_hl_auto_window24_l1_20260304.json",
    )
    parser.add_argument(
        "--extra-reports",
        nargs="*",
        default=[],
        help="可选：附加对比报告（例如已有的大组消融报告）",
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--output-dir", default="output/reports")
    parser.add_argument("--tag", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--groups", nargs="*", default=[])
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--train-window-months", type=int, default=24)
    parser.add_argument("--valid-window-months", type=int, default=2)
    parser.add_argument("--calibration-months", type=int, default=3)
    parser.add_argument("--sign-threshold", type=float, default=0.02)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--w3", type=float, default=0.1)
    parser.add_argument("--w5", type=float, default=0.45)
    parser.add_argument("--w10", type=float, default=0.45)
    parser.add_argument("--loss-type", choices=["l1", "ic_aware", "rank_aware", "ic_rank_aware"], default="l1")
    parser.add_argument("--loss-alpha", type=float, default=0.3)
    parser.add_argument("--ic-rank-beta", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-compare", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    group_map = GROUP_SETS[args.group_set]
    groups = [g for g in args.groups if g]
    if not groups:
        groups = list(group_map.keys())
    invalid_groups = [g for g in groups if g not in group_map]
    if invalid_groups:
        raise ValueError(f"unknown groups: {invalid_groups}; allowed={sorted(group_map.keys())}")

    base_dataset_dir = Path(args.base_dataset_dir)
    baseline_report = Path(args.baseline_report)
    if not baseline_report.exists():
        raise FileNotFoundError(f"baseline report not found: {baseline_report}")

    workspace = (
        Path(args.workspace)
        if str(args.workspace).strip()
        else Path("data/datasets/ablations/dim52_group_ablation") / args.group_set
    )
    output_dir = Path(args.output_dir)

    feature_bases = _infer_feature_bases(base_dataset_dir / "train.parquet", args.seq_len)
    _validate_groups(
        feature_bases,
        groups,
        group_map,
        require_full_coverage=GROUP_SET_REQUIRE_FULL_COVERAGE.get(args.group_set, False),
    )

    cfg = TrainArgs(
        seq_len=args.seq_len,
        train_window_months=args.train_window_months,
        valid_window_months=args.valid_window_months,
        calibration_months=args.calibration_months,
        sign_threshold=args.sign_threshold,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
        w3=args.w3,
        w5=args.w5,
        w10=args.w10,
        loss_type=args.loss_type,
        loss_alpha=args.loss_alpha,
        ic_rank_beta=args.ic_rank_beta,
        seed=args.seed,
    )

    reports: list[Path] = [baseline_report]
    for extra in args.extra_reports:
        p = Path(extra)
        if not p.exists():
            raise FileNotFoundError(f"extra report not found: {p}")
        reports.append(p)

    for group in groups:
        drop_features = group_map[group]
        out_dataset_dir = workspace / f"drop_{group}"
        if args.group_set == "base52":
            report_stem = f"lstm_dim52_ablation_drop_{group}_auto_window24_{args.loss_type}_{args.tag}"
        else:
            report_stem = (
                f"lstm_dim52_ablation_{args.group_set}_drop_{group}_auto_window24_{args.loss_type}_{args.tag}"
            )
        report_path = output_dir / f"{report_stem}.json"
        oos_path = output_dir / f"{report_stem}_oos.parquet"

        print(f"\n=== group: {group} (drop {len(drop_features)} features) ===")
        _drop_group_dataset(base_dataset_dir, out_dataset_dir, drop_features, args.seq_len)

        if not args.skip_train:
            _run_train_for_group(out_dataset_dir, report_path, oos_path, cfg)

        reports.append(report_path)

    if not args.skip_compare:
        compare_prefix = "dim52_group_ablation" if args.group_set == "base52" else f"dim52_{args.group_set}_ablation"
        _run_compare(reports, args.tag, output_dir, compare_prefix=compare_prefix)

    print("\nDone. Reports:")
    for p in reports:
        print(f"- {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
