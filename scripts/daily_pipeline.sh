#!/bin/bash
# 生产环境日频流水线包装脚本

set -euo pipefail

# 环境配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 激活虚拟环境（如果存在）
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export TUSHARE_TOKEN="${TUSHARE_TOKEN:-}"  # 从环境变量读取

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 创建日志目录（如果不存在）
mkdir -p logs

# 获取当前日期（YYYYMMDD 格式）
TARGET_DATE="${1:-$(date +%Y%m%d)}"

# 记录开始时间
echo "=== Daily Pipeline Start: $(date) ===" | tee -a workspace/runs/pipeline.log

# 执行流水线
python scripts/daily_pipeline.py \
    --date "$TARGET_DATE" \
    --config configs/pipeline.yaml \
    2>&1 | tee -a workspace/runs/pipeline.log

EXIT_CODE=$?

# 记录结束时间
echo "=== Daily Pipeline End: $(date), Exit Code: $EXIT_CODE ===" | tee -a workspace/runs/pipeline.log

exit $EXIT_CODE
