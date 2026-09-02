#!/usr/bin/env bash
# 联调复现一键入口：数据 → 数据集 → 模型 → 评估（复现性审计 G2 闭环）。
#
# 用法：
#   bash scripts/repro_full_chain.sh                     # 全链路（训练，~2h）
#   bash scripts/repro_full_chain.sh --skip-training     # 数据→数据集→评估（用已有 OOS，~10min）
#   bash scripts/repro_full_chain.sh --dry-run           # 只验证环境与前置产物
#
# 前置：conda env py311-private；.env 含 TUSHARE_TOKEN；数据湖已落盘（NEXT_STEPS 1.1-1.5）。
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

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
