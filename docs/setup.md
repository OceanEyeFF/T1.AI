# 环境配置与快速开始指南

本文档提供项目的环境配置和端到端使用流程。

---

## 1. 前置准备

### 1.1 获取 TuShare Token

1. 访问 [TuShare Pro](https://tushare.pro/register) 注册账号
2. 登录后进入「个人中心」→「接口TOKEN」
3. 复制 Token

### 1.2 安装 Conda 环境（推荐）

```bash
# Linux
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# macOS
brew install miniconda
```

---

## 2. 环境安装

### 方法A：使用 Conda（推荐）

```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate ashare-lab

# 安装项目（开发模式）
pip install -e ".[dev]"
```

### 方法B：使用 pip

```bash
python -m pip install -e ".[dev]"
```

---

## 3. 配置环境变量

### 方法1：使用 .env 文件（推荐）

```bash
# 编辑 .env 文件
cp .env.example .env
vim .env

# 设置内容
TUSHARE_TOKEN=your_actual_token_here
CACHE_DIR=data/cache
OUTPUT_DIR=output
MODEL_DIR=models
```

### 方法2：直接导出

```bash
export TUSHARE_TOKEN="your_token_here"
```

### 方法3：设置到 Conda 环境

```bash
conda env config vars set TUSHARE_TOKEN="your_token_here"
conda deactivate && conda activate ashare-lab
```

---

## 4. 创建必要目录

```bash
mkdir -p data/{cache,datasets,universe}
mkdir -p output/{recommendations,validations,reports}
mkdir -p models logs
```

---

## 5. 验证安装

```bash
# 运行测试
pytest tests/

# 验证 Token
python -c "
import os
token = os.environ.get('TUSHARE_TOKEN')
if token:
    print(f'Token 已设置: {token[:8]}...{token[-4:]}')
else:
    print('Token 未设置')
"
```

---

## 6. 快速使用流程

### Step 1: 准备股票池

```bash
python scripts/build_universe.py --date 20241231
```

### Step 2: 构建数据集

```bash
python scripts/build_sequence_dataset.py \
  --start 20200101 --end 20241231 \
  --seq-len 30 --output-dir data/datasets
```

### Step 3: 训练模型

```bash
python scripts/train_mtl.py \
  --config configs/model_mtl.yaml \
  --train-data data/datasets/train.parquet \
  --valid-data data/datasets/valid.parquet
```

### Step 4: 生成推荐

```bash
python scripts/generate_daily_recommendations.py \
  --model-path models/best_mtl.pt \
  --date 20250115 --top-n 10
```

### Step 5: 验证推荐

```bash
python scripts/validate_recommendations.py \
  --recommendation-date 20250115 \
  --validation-date 20250120
```

### Step 6: 每日自动化

```bash
python scripts/daily_pipeline.py --date 20250116
```

---

## 7. 常见问题

### Q1: Token 未设置

```bash
# 检查
echo $TUSHARE_TOKEN

# 重新设置
export TUSHARE_TOKEN="your_token"
```

### Q2: CUDA 内存不足

修改 `configs/model_mtl.yaml`:
```yaml
training:
  batch_size: 16  # 减小 batch size
```

### Q3: Conda 环境问题

```bash
# 删除并重建
conda env remove -n ashare-lab
conda env create -f environment.yml
```

---

## 8. IDE 配置

### VS Code

编辑 `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "~/miniconda3/envs/ashare-lab/bin/python"
}
```

### Jupyter Notebook

```bash
conda activate ashare-lab
python -m ipykernel install --user --name=ashare-lab
```

---

**相关文档：**
- [约束规则](constraints.md) - 交易硬约束
- [数据契约](data_contract.md) - 数据格式规范
- [交易协议](protocol.md) - 执行时序定义
