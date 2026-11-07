#!/usr/bin/env bash
# 联调复现一键入口：数据 → 数据集 → 模型 → 评估（复现性审计 G2 闭环）。
#
# 用法：
#   bash scripts/repro_full_chain.sh                     # 全链路（训练，~2h）
#   bash scripts/repro_full_chain.sh --skip-training     # 仅当已有 OOS 与重建数据集 ID 一致时可跳训
#   bash scripts/repro_full_chain.sh --dry-run           # 只验证环境与前置产物
#
# 前置：conda env py311-private；.env 含 TUSHARE_TOKEN；数据湖已落盘（NEXT_STEPS 1.1-1.5）。
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
mkdir -p workspace/runs outputs/reports

SKIP_TRAINING=0
DRY_RUN=0
for arg in "$@"; do
  case "${arg}" in
    --skip-training) SKIP_TRAINING=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown arg: ${arg}" >&2; exit 2 ;;
  esac
done

# ---------- 环境与前置校验 ----------
echo "[1/5] 环境校验 ..."
if ! command -v python >/dev/null 2>&1; then
  echo "ERROR: python 缺失（请 conda activate py311-private）" >&2
  exit 1
fi
py_major_minor="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "${py_major_minor}" != "3.11" ]]; then
  echo "ERROR: 需要 Python 3.11（当前 ${py_major_minor}）" >&2
  exit 1
fi
if [[ -z "${TUSHARE_TOKEN:-}" ]]; then
  echo "ERROR: TUSHARE_TOKEN 未设置（source .env）" >&2
  exit 1
fi
lake_ok="$(python - <<'PY'
from pathlib import Path
p = Path("inputs/data/cache/tushare_qfq")
if not p.is_dir() or not any(p.iterdir()):
    print("0")
else:
    print("1")
PY
)"
if [[ "${lake_ok}" != "1" ]]; then
  echo "ERROR: 数据湖缺失（inputs/data/cache/tushare_qfq 为空）——先执行 NEXT_STEPS 1.3/1.4 拉取" >&2
  exit 1
fi
echo "      环境 OK（py311 + token + lake）"

PROFILE="inputs/configs/profiles/sequence_dataset_baseline.toml"
DATASET_DIR="$(
  python - "$PROFILE" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))["build_sequence_dataset"]
print(cfg["output_dir"])
PY
)"

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "[dry-run] 前置满足。dataset_dir=${DATASET_DIR}"
  echo "[dry-run] 将执行：build → rolling(LSTM/XGB) → audit → compare → panel → sanity"
  exit 0
fi

# ---------- 数据集 -------------
echo "[2/5] 构建数据集（${DATASET_DIR}）..."
python scripts/build_sequence_dataset.py --config-file "${PROFILE}" 2>&1 | tail -2

# ---------- 训练 ----------
if [[ "${SKIP_TRAINING}" == "1" ]]; then
  echo "[3/5] 跳过训练（--skip-training），使用已有 OOS"
  LSTMOOS="outputs/reports/lstm_baseline_v2_20260813_oos.parquet"
  LSTMRPT="outputs/reports/lstm_baseline_v2_20260813.json"
  XGBOOS="outputs/reports/xgb_baseline_v2_20260813_oos.parquet"
  XGBRPT="outputs/reports/xgb_baseline_v2_20260813.json"
else
  echo "[3/5] LSTM rolling 训练（后台）..."
  nohup python -u scripts/run_lstm_rolling_retrain_dim19_regime.py \
    --dataset-dir "${DATASET_DIR}" --feature-mode auto \
    --save-oos-parquet outputs/reports/lstm_baseline_v2_20260813_oos.parquet \
    --report outputs/reports/lstm_baseline_v2_20260813.json \
    > workspace/runs/repro_lstm.log 2>&1 &
  lstm_pid=$!
  echo "      LSTM pid=${lstm_pid}（日志 workspace/runs/repro_lstm.log）"

  echo "      XGB rolling 训练（前台，CPU 多核）..."
  python -u scripts/run_xgboost_rolling_retrain_regime.py \
    --dataset-dir "${DATASET_DIR}" \
    --save-oos-parquet outputs/reports/xgb_baseline_v2_20260813_oos.parquet \
    --report outputs/reports/xgb_baseline_v2_20260813.json

  echo "      等待 LSTM 完成..."
  wait "${lstm_pid}"

  LSTMOOS="outputs/reports/lstm_baseline_v2_20260813_oos.parquet"
  LSTMRPT="outputs/reports/lstm_baseline_v2_20260813.json"
  XGBOOS="outputs/reports/xgb_baseline_v2_20260813_oos.parquet"
  XGBRPT="outputs/reports/xgb_baseline_v2_20260813.json"
fi

# ---------- 数据集 / OOS 身份校验 ----------
python - "${DATASET_DIR}" "${LSTMRPT}" "${LSTMOOS}" "${XGBRPT}" "${XGBOOS}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

dataset_dir = Path(sys.argv[1])
dataset_metadata = json.loads((dataset_dir / "metadata.json").read_text(encoding="utf-8"))
dataset_id = dataset_metadata.get("dataset_id")
if not dataset_id:
    raise SystemExit(f"ERROR: dataset metadata has no dataset_id: {dataset_dir}")
dataset_contract = dataset_metadata.get("feature_contract")
if not isinstance(dataset_contract, dict) or not dataset_contract.get("feature_contract_hash"):
    raise SystemExit(f"ERROR: dataset metadata has no Feature Contract: {dataset_dir}")

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

for report_text, oos_text in ((sys.argv[2], sys.argv[3]), (sys.argv[4], sys.argv[5])):
    report_path = Path(report_text)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    config = report.get("config") if isinstance(report.get("config"), dict) else {}
    metadata = report.get("experiment_metadata") if isinstance(report.get("experiment_metadata"), dict) else {}
    report_dataset_id = config.get("dataset_id") or metadata.get("dataset_id")
    if report_dataset_id != dataset_id:
        raise SystemExit(
            "ERROR: OOS report dataset_id mismatch; retrain is required: "
            f"report={report_path} report_id={report_dataset_id!r} dataset_id={dataset_id!r}"
        )
    if config.get("feature_contract_hash") != dataset_contract["feature_contract_hash"]:
        raise SystemExit(
            "ERROR: OOS report Feature Contract mismatch; retrain is required: "
            f"report={report_path}"
        )
    artifact = report.get("oos_artifact")
    if not isinstance(artifact, dict):
        raise SystemExit(
            "ERROR: report has no OOS artifact identity; legacy OOS cannot be reused: "
            f"{report_path}"
        )
    oos_path = Path(oos_text)
    if not oos_path.exists():
        raise SystemExit(f"ERROR: OOS parquet missing: {oos_path}")
    if artifact.get("sha256") != sha256_file(oos_path):
        raise SystemExit(f"ERROR: OOS parquet hash mismatch; retrain is required: {oos_path}")
    frame = pd.read_parquet(oos_path)
    if artifact.get("rows") != len(frame) or artifact.get("columns") != list(frame.columns):
        raise SystemExit(f"ERROR: OOS parquet shape/schema mismatch; retrain is required: {oos_path}")
    if artifact.get("dataset_id") != dataset_id:
        raise SystemExit(f"ERROR: OOS artifact dataset_id mismatch; retrain is required: {oos_path}")
    if artifact.get("feature_contract_hash") != dataset_contract["feature_contract_hash"]:
        raise SystemExit(f"ERROR: OOS artifact Feature Contract mismatch; retrain is required: {oos_path}")
PY

# ---------- 评估链 ----------
TAG="$(date +%Y%m%d)_repro"
echo "[4/5] 评估链（tag=${TAG}）..."
python scripts/audit_ic_reports.py --reports "${LSTMRPT}" "${XGBRPT}" --tag "${TAG}"
python scripts/compare_ic_reports.py --reports "${LSTMRPT}" "${XGBRPT}" \
  --metric-source raw --monthly-source raw --daily-cs-mode required --check-protocol --tag "${TAG}"
python scripts/compare_trade_like_panels.py --reports "${LSTMRPT}" "${XGBRPT}" --tag "${TAG}"
for m in lstm xgb; do
  for h in 5 10; do
    python scripts/run_sanity_checks.py \
      --oos-parquet "outputs/reports/${m}_baseline_v2_20260813_oos.parquet" \
      --horizon "${h}" --output "outputs/reports/sanity_${m}_v2_repro_h${h}.json"
  done
done

echo "[5/5] 完成。产物：outputs/reports/ic_*_${TAG}.*、ic_trade_panel_${TAG}.md、sanity_*_repro_*.json"
echo "      评估链比对数字：ic_monthly_comparison_${TAG}.md（对比基线数字可检查复现一致性）"
