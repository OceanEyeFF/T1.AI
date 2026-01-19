# 快速开始指南 - 训练与测试

本文档提供**端到端的训练、测试和推荐生成**完整流程。

---

## 📋 前置准备

### 1. 环境变量设置

```bash
# 设置TuShare Token（必需）
export TUSHARE_TOKEN="your_tushare_token_here"

# 可选：设置缓存和输出目录
export CACHE_DIR="data/cache"
export OUTPUT_DIR="output"
export MODEL_DIR="models"
```

**获取TuShare Token：**
1. 访问 https://tushare.pro/register
2. 注册账号并获取Token
3. 将Token设置为环境变量

### 2. 创建必要目录

```bash
mkdir -p data/{cache,datasets,recommendation_history}
mkdir -p output/{recommendations,validations,reports}
mkdir -p models
mkdir -p logs
mkdir -p configs
```

### 3. 安装依赖

```bash
# 如果还没安装
python -m pip install -e ".[dev]"
```

---

## 🚀 完整训练流程（首次运行）

### Step 1: 准备股票池

**目的：** 获取可交易的A股股票列表（排除ST/科创/创业/北交）

```bash
python scripts/prepare_universe.py \
  --output data/universe.csv \
  --min-price 1.0 \
  --min-volume 1000
```

**预期输出：**
```
✅ 股票池构建完成
   总股票数: 4500+
   过滤后: 3200+
   已保存: data/universe.csv
```

**检查结果：**
```bash
head data/universe.csv
```

---

### Step 2: 数据拉取（TuShare）

**目的：** 拉取股票池中所有股票的历史行情数据

```bash
python scripts/fetch_data.py \
  --symbols-file data/universe.csv \
  --start-date 20200101 \
  --end-date 20241231 \
  --cache-dir data/cache
```

**参数说明：**
- `--symbols-file`: 股票池文件（从Step 1生成）
- `--start-date`: 开始日期（YYYYMMDD格式）
- `--end-date`: 结束日期
- `--cache-dir`: 缓存目录（分区存储，可增量拉取）

**预期输出：**
```
拉取进度: 100%|████████████| 3200/3200 [15:30<00:00]
✅ 数据拉取完成
   成功: 3180 只股票
   失败: 20 只股票（已跳过）
   缓存位置: data/cache/tushare/
```

**注意：** 首次拉取约需15-30分钟（取决于网络和TuShare限流）

---

### Step 3: 特征计算

**目的：** 计算所有技术特征（动量、斜率、RSI、MACD等）

```bash
python scripts/compute_features.py \
  --cache-dir data/cache \
  --symbols-file data/universe.csv \
  --output data/features.parquet
```

**预期输出：**
```
计算特征中...
  动量特征: ✅ return_1d, return_5d, return_20d
  价格斜率: ✅ price_slope_20d
  相对交易量: ✅ volume_ratio
  技术指标: ✅ rsi_14, macd_line, macd_signal, bollinger_deviation

✅ 特征计算完成
   特征数量: 10
   样本数量: 3200 股票 × 1200 天 = 3,840,000 样本
   已保存: data/features.parquet
```

**检查结果：**
```bash
python -c "import pandas as pd; df=pd.read_parquet('data/features.parquet'); print(df.info()); print(df.head())"
```

---

### Step 4: 标签计算

**目的：** 计算多时间跨度标签（3D/5D/10D未来收益）

```bash
python scripts/compute_labels.py \
  --cache-dir data/cache \
  --symbols-file data/universe.csv \
  --horizons 3 5 10 \
  --output data/labels.parquet
```

**预期输出：**
```
计算标签中...
  label_3d: ✅ (未来3日收益)
  label_5d: ✅ (未来5日收益)
  label_10d: ✅ (未来10日收益)

停牌检测: ✅ 已自动设为NaN

✅ 标签计算完成
   标签数量: 3
   有效样本: 3,520,000 (NaN占比 8.3%)
   已保存: data/labels.parquet
```

---

### Step 5: 构建序列数据集

**目的：** 将特征和标签转换为序列格式 `[batch, seq_len, n_feat]`

```bash
python scripts/build_sequence_dataset.py \
  --features data/features.parquet \
  --labels data/labels.parquet \
  --seq-len 30 \
  --train-ratio 0.7 \
  --valid-ratio 0.15 \
  --output-dir data/datasets
```

**参数说明：**
- `--seq-len`: 序列长度（默认30日）
- `--train-ratio`: 训练集比例（70%）
- `--valid-ratio`: 验证集比例（15%）
- 测试集比例自动计算（15%）

**预期输出：**
```
构建序列数据集...
  序列长度: 30
  特征维度: 10

Walk-forward划分:
  训练集: 2,450,000 样本 (70%)
  验证集: 525,000 样本 (15%)
  测试集: 525,000 样本 (15%)

✅ 数据集构建完成
   已保存: data/datasets/train.parquet
          data/datasets/valid.parquet
          data/datasets/test.parquet
```

**检查结果：**
```bash
python -c "import pandas as pd; print('Train:', pd.read_parquet('data/datasets/train.parquet').shape)"
```

---

### Step 6: 训练MTL Transformer

**目的：** 训练多任务学习模型（共享编码器 + 3个回归头）

```bash
python scripts/train_mtl.py \
  --config configs/model_mtl.yaml \
  --train-data data/datasets/train.parquet \
  --valid-data data/datasets/valid.parquet \
  --output-dir models
```

**预期输出：**
```
模型配置:
  input_dim: 10
  d_model: 128
  n_layers: 4
  n_heads: 4
  seq_len: 30

训练开始...

Epoch 1/50
  Train Loss: 0.0234 | Valid Loss: 0.0251 | Valid IC: 0.0423
  ⏱️  耗时: 3分20秒

Epoch 2/50
  Train Loss: 0.0219 | Valid Loss: 0.0245 | Valid IC: 0.0512
  ✅ Best model saved! (IC提升)
  ⏱️  耗时: 3分18秒

...

Epoch 15/50
  Train Loss: 0.0187 | Valid Loss: 0.0238 | Valid IC: 0.0568
  ✅ Best model saved! (IC提升)

Epoch 16-20: IC无提升
Early stopping triggered! (patience=5)

✅ 训练完成
   最佳验证集IC: 0.0568
   模型保存: models/best_mtl.pt
   训练日志: logs/train_mtl.log
```

**检查模型文件：**
```bash
ls -lh models/
# 预期看到: best_mtl.pt, latest.pt
```

---

### Step 7: 测试集评估

**目的：** 在测试集上评估模型泛化能力

```bash
python scripts/evaluate_model.py \
  --model-path models/best_mtl.pt \
  --test-data data/datasets/test.parquet \
  --output output/test_results.json
```

**预期输出：**
```
加载模型: models/best_mtl.pt
加载测试集: 525,000 样本

评估中...

测试集结果:
┌──────────┬──────────┬──────────┬──────────┐
│ Horizon  │   IC     │ Rank IC  │   MAE    │
├──────────┼──────────┼──────────┼──────────┤
│   3D     │  0.0542  │  0.0689  │  0.0231  │
│   5D     │  0.0558  │  0.0712  │  0.0245  │
│  10D     │  0.0521  │  0.0665  │  0.0268  │
└──────────┴──────────┴──────────┴──────────┘

✅ 测试评估完成
   结果已保存: output/test_results.json
```

**解读：**
- **IC > 0.05**: ✅ 模型具有预测能力
- **Rank IC > IC**: ✅ 排序能力强于绝对预测
- **MAE < 0.03**: ✅ 预测误差可接受

---

## 🎯 生成推荐榜单

### Step 8: 生成今日推荐

**目的：** 基于训练好的模型，生成今日的3×Top-10推荐榜单

```bash
python scripts/generate_daily_recommendations.py \
  --model-path models/best_mtl.pt \
  --date 20250115 \
  --top-n 10 \
  --output-dir output/recommendations
```

**预期输出：**
```
生成推荐榜单: 2025-01-15

加载模型: models/best_mtl.pt
获取股票池: 3200 只可交易股票
构建特征序列: ✅

模型推理中...
  3D预测: ✅
  5D预测: ✅
  10D预测: ✅

生成推荐榜单:
  3D Top-10: ✅
  5D Top-10: ✅
  10D Top-10: ✅

✅ 推荐榜单已生成
   JSON: output/recommendations/20250115.json
   CSV:  output/recommendations/20250115_3d.csv
         output/recommendations/20250115_5d.csv
         output/recommendations/20250115_10d.csv
   Markdown: output/recommendations/20250115.md
```

**查看推荐结果：**
```bash
cat output/recommendations/20250115.md
```

**示例输出：**
```markdown
# 多时间跨度股票推荐榜单

**日期：** 2025-01-15

## 3D 推荐（短期）

| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |
|------|------|------|----------|--------|----------|
| 1 | 600519 | 贵州茅台 | 2.34% | 0.85 | 强势动量（20日+18%）\| RSI=75 \| 成交量放大 |
| 2 | 000333 | 美的集团 | 2.12% | 0.82 | RSI中性偏强(62.3) \| 20日动量温和(+8%) |
| ... |

## 5D 推荐（中期）

| 排名 | 代码 | 名称 | 预测收益 | 置信度 | 推荐理由 |
|------|------|------|----------|--------|----------|
| 1 | 601318 | 中国平安 | 4.56% | 0.87 | ... |
...
```

---

## ✅ 验证推荐准确性

### Step 9: 验证前一日推荐

**目的：** 验证前一日推荐的准确性（需要等实际收益数据）

**前提：** 已生成20250115的推荐，现在是20250120（3个交易日后）

```bash
python scripts/validate_recommendations.py \
  --recommendation-file output/recommendations/20250115.json \
  --recommendation-date 20250115 \
  --validation-date 20250120 \
  --output output/validations/20250115.json
```

**预期输出：**
```
验证推荐: 2025-01-15

加载推荐结果: output/recommendations/20250115.json
获取实际收益数据: 2025-01-16 至 2025-01-20

==================================================
3D 验证结果
==================================================
命中率: 70.0%
平均收益: 1.85%
IC: 0.0534
Rank IC: 0.0678
Top-10累计收益: 19.2%
基准收益: 0.8% (沪深300)
超额收益: 1.05%

==================================================
5D 验证结果
==================================================
命中率: 80.0%
平均收益: 3.42%
IC: 0.0612
Rank IC: 0.0745
Top-10累计收益: 38.5%
基准收益: 1.2%
超额收益: 2.22%

==================================================
10D 验证结果
==================================================
命中率: 60.0%
平均收益: 5.12%
IC: 0.0498
Rank IC: 0.0623
Top-10累计收益: 56.8%
基准收益: 2.1%
超额收益: 3.02%

✅ 验证完成
   验证报告已保存: output/validations/20250115.json
```

**解读：**
- **命中率 > 60%**: ✅ 大部分推荐股票上涨
- **IC > 0.05**: ✅ 预测能力良好
- **超额收益 > 0**: ✅ 跑赢基准（沪深300）

---

## 🔄 完整Pipeline测试

### Step 10: 运行每日自动化流程

**目的：** 测试完整的每日Pipeline（数据拉取 → 训练 → 推荐 → 验证）

```bash
python scripts/daily_pipeline.py \
  --config configs/data_source.yaml \
  --date 20250116
```

**预期输出：**
```
============================================================
每日Pipeline开始执行 - 20250116
============================================================

Step 1: 加载配置文件
  ✅ 配置加载完成

Step 2: TuShare增量拉取今日数据
  ✅ 数据拉取成功 (3200 只股票)

Step 3: 计算特征（滚动30日窗口）
  ✅ 特征计算完成，共 10 个特征

Step 4: 计算标签（3D/5D/10D）
  ✅ 标签计算完成

Step 5: 增量训练模型
  已加载checkpoint: models/latest.pt
  已冻结前2层编码器
    Epoch 1/2: Train Loss=0.0189, Valid Loss=0.0241, IC=0.0572
    Epoch 2/2: Train Loss=0.0186, Valid Loss=0.0239, IC=0.0579
  ✅ 新checkpoint已保存

Step 6: 生成推荐榜单（3×Top-10）
  ✅ 推荐榜单生成成功
  ✅ 推荐结果已保存: output/recommendations/20250116.json

Step 7: 验证前一日推荐（20250115）
  ✅ 验证完成
    3d: 命中率=70.0%, IC=0.0534, 超额收益=1.05%
    5d: 命中率=80.0%, IC=0.0612, 超额收益=2.22%
    10d: 命中率=60.0%, IC=0.0498, 超额收益=3.02%

Step 8: 模型性能监控
  ✅ 3d: 平均IC=0.0542，性能正常
  ✅ 5d: 平均IC=0.0568，性能正常
  ✅ 10d: 平均IC=0.0531，性能正常
  ✅ 模型监控完成

============================================================
每日Pipeline执行完成 - 20250116
============================================================
```

**检查日志：**
```bash
tail -f logs/daily_pipeline.log
```

---

## 📊 月度报告生成

### Step 11: 生成月度统计报告

**目的：** 汇总本月推荐系统表现

```bash
python scripts/evaluate_recommendation.py \
  --year-month 202501 \
  --output output/reports/202501_report.md
```

**预期输出：**
```
生成月度报告: 2025-01

查询历史数据: 2025-01-01 至 2025-01-31

统计指标:
  3D: 推荐天数=20, 平均命中率=68%, 平均IC=0.0542
  5D: 推荐天数=20, 平均命中率=75%, 平均IC=0.0568
  10D: 推荐天数=20, 平均命中率=62%, 平均IC=0.0531

✅ 月度报告已生成: output/reports/202501_report.md
```

**查看报告：**
```bash
cat output/reports/202501_report.md
```

---

## 🛠️ 常见问题排查

### Q1: TuShare数据拉取失败

**错误信息：**
```
❌ 数据拉取失败: No token found
```

**解决方案：**
```bash
# 检查环境变量
echo $TUSHARE_TOKEN

# 如果为空，重新设置
export TUSHARE_TOKEN="your_token_here"
```

---

### Q2: 训练过程OOM（内存不足）

**错误信息：**
```
RuntimeError: CUDA out of memory
```

**解决方案：**
```bash
# 方法1: 减小batch size
# 修改 configs/model_mtl.yaml
training:
  batch_size: 16  # 原来是32

# 方法2: 减小序列长度
# 修改 scripts/build_sequence_dataset.py
--seq-len 20  # 原来是30
```

---

### Q3: 验证集IC过低（< 0.05）

**可能原因：**
1. 特征不足（当前只有10个）
2. 过拟合（训练集loss很低，验证集loss高）
3. 数据质量问题

**解决方案：**
```bash
# 方法1: 增加特征
# 修改 scripts/compute_features.py，添加更多技术指标

# 方法2: 增强正则化
# 修改 configs/model_mtl.yaml
training:
  dropout: 0.2      # 原来是0.1
  weight_decay: 1e-4  # 原来是1e-5

# 方法3: 检查数据质量
python scripts/check_data_quality.py
```

---

## 📝 验收清单

完成所有步骤后，检查以下验收项：

### 训练阶段

- [ ] 训练集、验证集、测试集成功生成
- [ ] 模型训练收敛（验证集IC > 0.05）
- [ ] 测试集IC > 0.05
- [ ] checkpoint文件正常保存（models/best_mtl.pt）

### 推荐阶段

- [ ] 成功生成3×Top-10推荐榜单
- [ ] 输出格式正确（JSON/CSV/Markdown）
- [ ] 推荐理由合理（无异常值）

### 验证阶段

- [ ] 推荐验证成功（命中率、IC、超额收益）
- [ ] 验证指标在合理范围内
- [ ] 历史数据成功持久化（SQLite）

### 自动化阶段

- [ ] daily_pipeline.py 成功运行
- [ ] 增量训练正常执行
- [ ] 模型监控无异常

---

## 🚀 下一步

完成所有验收后，你可以：

1. **配置Cron定时任务** - 每日自动运行（见 [docs/tasks/phase3_automation.md](tasks/phase3_automation.md)）
2. **优化模型** - 尝试LSTM、增加特征、调整超参数
3. **Web可视化** - 构建推荐榜单查看界面
4. **邮件/微信通知** - 自动推送推荐结果

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-15
**版本：** v1.0
