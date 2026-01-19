#!/bin/bash

# Conda 环境快速设置脚本
# 用法：bash scripts/setup_conda_env.sh

set -e  # 遇到错误立即退出

echo "🐍 开始设置 A-Share Lab Conda 环境..."
echo ""

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# 检查 conda 是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ 错误：未找到 conda"
    echo ""
    echo "请先安装 Anaconda 或 Miniconda："
    echo "  - Anaconda: https://www.anaconda.com/download"
    echo "  - Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ 检测到 conda: $(conda --version)"
echo ""

# 检查环境是否已存在
ENV_NAME="ashare-lab"
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "⚠️  环境 '$ENV_NAME' 已存在"
    read -p "是否删除并重新创建？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  删除现有环境..."
        conda env remove -n "$ENV_NAME" -y
    else
        echo "❌ 取消安装"
        exit 0
    fi
fi

# 创建 conda 环境
echo "📦 创建 conda 环境（可能需要几分钟）..."
conda env create -f environment.yml

echo ""
echo "✅ Conda 环境创建成功！"
echo ""

# 激活环境并安装项目
echo "📥 安装项目到开发模式..."
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# 安装项目（开发模式）
pip install -e ".[dev]"

echo ""
echo "🎉 安装完成！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "下一步："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  激活环境："
echo "   conda activate $ENV_NAME"
echo ""
echo "2️⃣  加载环境变量："
echo "   source scripts/load_env.sh"
echo ""
echo "3️⃣  运行测试："
echo "   pytest tests/"
echo ""
echo "4️⃣  开始训练："
echo "   python scripts/build_sequence_dataset.py \\"
echo "     --start 20240101 --end 20240131 \\"
echo "     --symbols 600519,000333,601318 \\"
echo "     --source tushare --seq-len 30"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
