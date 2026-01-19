# 实际可用命令速查表

**基于当前代码库的真实脚本**

---

## 🔧 前置准备

```bash
# 1. 设置环境变量
export TUSHARE_TOKEN="your_tushare_token_here"

# 2. 创建目录
mkdir -p data/{cache,datasets,universe} output/{recommendations,validations,reports} models logs

# 3. 安装依赖
python -m pip install -e ".[dev]"
```

---

## 🚀 完整训练流程

### Step 1: 准备股票池 ✅

```bash
# 使用 build_universe.py（已存在）
python scripts/build_universe.py --date 20241231

# 输出位置: data/cache/universe/20241231.csv
```

### Step 2: 数据拉取 ⚠️

**方法A：使用现有脚本（如果有TuShare集成）**

检查是否有数据拉取功能：
```bash
# 检查 build_dataset.py 或 build_dataset_multi_stock.py
python scripts/build_dataset_multi_stock.py --help
```

**方法B：手动创建数据拉取脚本**

如果没有现成的，浮浮酱可以帮主人创建一个 `scripts/fetch_data.py` 脚本 (๑•̀ㅂ•́)و✧

### Step 3-5: 特征、标签、序列构建 ✅

```bash
# 使用 build_sequence_dataset.py（已存在）
python scripts/build_sequence_dataset.py \
  --symbols-file data/cache/universe/20241231.csv \
  --start-date 20200101 \
  --end-date 20241231 \
  --seq-len 30 \
  --output-dir data/datasets
```

**注意：** 这个脚本可能已经集成了特征计算、标签计算和序列构建功能 ✨

### Step 6: 训练MTL Transformer ✅

```bash
python scripts/train_mtl.py \
  --config configs/model_mtl.yaml \
  --train-data data/datasets/train.parquet \
  --valid-data data/datasets/valid.parquet \
  --output-dir models
```

### Step 7: 模型评估 ✅

```bash
python scripts/evaluate_model.py \
  --model-path models/best_mtl.pt \
  --test-data data/datasets/test.parquet \
  --output output/test_results.json
```

### Step 8: 生成推荐 ✅

```bash
python scripts/generate_daily_recommendations.py \
  --model-path models/best_mtl.pt \
  --date 20250115 \
  --top-n 10 \
  --output-dir output/recommendations
```

### Step 9: 验证推荐 ✅

```bash
python scripts/validate_recommendations.py \
  --recommendation-file output/recommendations/20250115.json \
  --recommendation-date 20250115 \
  --validation-date 20250120
```

### Step 10: 月度评估 ✅

```bash
python scripts/evaluate_recommendation.py \
  --year-month 202501 \
  --output output/reports/202501_report.md
```

### Step 11: 完整Pipeline ✅

```bash
python scripts/daily_pipeline.py \
  --config configs/data_source.yaml \
  --date 20250116
```

---

## 🎯 最简化流程（快速测试）

如果主人想快速测试整个流程，浮浮酱建议这样做 φ(≧ω≦*)♪

### 方案A：使用小股票池（推荐）

```bash
# 1. 创建测试股票池（10只股票）
cat > data/test_universe.csv << EOF
symbol,name
600519,贵州茅台
000333,美的集团
601318,中国平安
000858,五粮液
600036,招商银行
601166,兴业银行
600276,恒瑞医药
600900,长江电力
601288,农业银行
601398,工商银行
EOF

# 2. 构建数据集（这一步可能需要调整脚本参数）
python scripts/build_sequence_dataset.py \
  --symbols-file data/test_universe.csv \
  --start-date 20240101 \
  --end-date 20241231 \
  --seq-len 30 \
  --output-dir data/datasets

# 3. 训练模型
python scripts/train_mtl.py \
  --config configs/model_mtl.yaml \
  --train-data data/datasets/train.parquet \
  --valid-data data/datasets/valid.parquet

# 4. 生成推荐
python scripts/generate_daily_recommendations.py \
  --model-path models/best_mtl.pt \
  --date 20250115
```

---

## ⚠️ 可能缺失的脚本

浮浮酱发现以下脚本可能需要创建：

### 1. `scripts/fetch_data.py` - 数据拉取脚本

**如果 build_sequence_dataset.py 没有集成数据拉取功能**

主人需要这个脚本吗？浮浮酱可以立即创建 (๑•̀ㅂ•́)و✧

### 2. `scripts/compute_features.py` - 特征计算脚本

**如果需要独立的特征计算步骤**

### 3. `scripts/compute_labels.py` - 标签计算脚本

**如果需要独立的标签计算步骤**

---

## 💡 下一步建议

**主人现在可以：**

### 选项A：检查现有脚本功能

```bash
# 检查 build_sequence_dataset.py 的帮助信息
python scripts/build_sequence_dataset.py --help

# 检查是否已集成数据拉取、特征计算、标签计算
```

### 选项B：让浮浮酱创建缺失脚本

如果主人发现某些脚本缺失，浮浮酱可以立即帮主人创建 ฅ'ω'ฅ

### 选项C：直接测试现有流程

```bash
# 先尝试运行 build_sequence_dataset.py
# 看看会发生什么，然后根据报错调整
python scripts/build_sequence_dataset.py --help
```

---

**主人想选择哪个方案喵？** (๑•̀ㅂ•́)و✧

还是说主人想让浮浮酱**检查一下 build_sequence_dataset.py 的具体实现**，看看它是否已经包含了数据拉取和特征计算功能呢？ φ(≧ω≦*)♪
