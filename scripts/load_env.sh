#!/bin/bash

# 环境变量加载脚本
# 用法: source scripts/load_env.sh

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 检查 .env 文件是否存在
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 错误：未找到 .env 文件"
    echo "请先创建 .env 文件并设置 TUSHARE_TOKEN"
    echo ""
    echo "步骤："
    echo "1. 复制 .env.example 为 .env"
    echo "   cp .env.example .env"
    echo ""
    echo "2. 编辑 .env 文件，填入你的 TuShare Token"
    echo "   vim .env  # 或使用其他编辑器"
    echo ""
    echo "3. 重新运行此脚本"
    echo "   source scripts/load_env.sh"
    return 1
fi

# 加载环境变量
echo "📋 加载环境变量..."
set -a  # 自动导出所有变量
source "$ENV_FILE"
set +a

# 验证 TUSHARE_TOKEN
if [ -z "$TUSHARE_TOKEN" ] || [ "$TUSHARE_TOKEN" = "your_tushare_token_here" ]; then
    echo "⚠️  警告：TUSHARE_TOKEN 未设置或使用默认值"
    echo "请编辑 .env 文件并设置正确的 Token"
    echo ""
    echo "获取 Token："
    echo "  1. 访问 https://tushare.pro/register"
    echo "  2. 注册账号并获取 Token"
    echo "  3. 将 Token 填入 .env 文件"
    return 1
fi

# 显示加载的环境变量（隐藏 Token 敏感部分）
echo "✅ 环境变量加载成功"
echo ""
echo "配置信息："
echo "  TUSHARE_TOKEN: ${TUSHARE_TOKEN:0:8}****${TUSHARE_TOKEN: -4}  # 已隐藏"
echo "  CACHE_DIR: ${CACHE_DIR:-data/cache}"
echo "  OUTPUT_DIR: ${OUTPUT_DIR:-output}"
echo "  MODEL_DIR: ${MODEL_DIR:-models}"
echo ""
echo "✨ 现在可以运行脚本了！"
