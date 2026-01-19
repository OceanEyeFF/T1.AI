#!/bin/bash

# 数据清理脚本
# 用于清理生成的数据集和缓存

set -e

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "🧹 A-Share Lab 数据清理工具"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查数据集大小
DATASETS_DIR="data/datasets"
CACHE_DIR="data/cache"

if [ -d "$DATASETS_DIR" ]; then
    DATASETS_SIZE=$(du -sh "$DATASETS_DIR" 2>/dev/null | cut -f1)
    DATASETS_COUNT=$(find "$DATASETS_DIR" -name "*.parquet" 2>/dev/null | wc -l)
    echo "📊 数据集目录: $DATASETS_DIR"
    echo "   大小: $DATASETS_SIZE"
    echo "   文件数: $DATASETS_COUNT 个 .parquet 文件"
    echo ""
fi

if [ -d "$CACHE_DIR" ]; then
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
    CACHE_FILES=$(find "$CACHE_DIR" -type f 2>/dev/null | wc -l)
    echo "💾 缓存目录: $CACHE_DIR"
    echo "   大小: $CACHE_SIZE"
    echo "   文件数: $CACHE_FILES 个缓存文件"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "请选择清理选项："
echo ""
echo "1) 仅清理数据集 (data/datasets/*.parquet)"
echo "2) 仅清理缓存 (data/cache/)"
echo "3) 清理所有数据（数据集 + 缓存）"
echo "4) 取消"
echo ""
read -p "请输入选项 [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "🗑️  清理数据集..."
        if [ -d "$DATASETS_DIR" ]; then
            # 列出要删除的文件
            echo "即将删除以下文件："
            find "$DATASETS_DIR" -name "*.parquet" -type f
            echo ""
            read -p "确认删除？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                find "$DATASETS_DIR" -name "*.parquet" -type f -delete
                echo "✅ 数据集已清理"
            else
                echo "❌ 取消清理"
            fi
        else
            echo "⚠️  数据集目录不存在"
        fi
        ;;
    2)
        echo ""
        echo "🗑️  清理缓存..."
        if [ -d "$CACHE_DIR" ]; then
            CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
            echo "缓存目录大小: $CACHE_SIZE"
            echo ""
            read -p "确认删除所有缓存？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$CACHE_DIR"
                mkdir -p "$CACHE_DIR"
                echo "✅ 缓存已清理"
            else
                echo "❌ 取消清理"
            fi
        else
            echo "⚠️  缓存目录不存在"
        fi
        ;;
    3)
        echo ""
        echo "🗑️  清理所有数据..."
        echo "⚠️  警告：这将删除所有数据集和缓存！"
        echo ""
        read -p "确认删除所有数据？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -d "$DATASETS_DIR" ]; then
                find "$DATASETS_DIR" -name "*.parquet" -type f -delete
                echo "✅ 数据集已清理"
            fi
            if [ -d "$CACHE_DIR" ]; then
                rm -rf "$CACHE_DIR"
                mkdir -p "$CACHE_DIR"
                echo "✅ 缓存已清理"
            fi
            echo "✅ 清理完成！"
        else
            echo "❌ 取消清理"
        fi
        ;;
    4)
        echo ""
        echo "❌ 取消清理"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "完成！"
