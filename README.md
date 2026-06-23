# T1.AI — A 股低频量化研究框架

A 股市场中短周期（3d/5d/10d）多因子预测模型的**研究、训练、验证、推理**一体化框架。

---

## 目录结构（三区模型）

```
inputs/          ← 数据缓存 + 选股池 + 配置档案
workspace/       ← checkpoint + 运行日志 + 认证注册表
outputs/         ← 预测 + 报告 + 交易信号
src/ashare_lab/  ← 模型代码（独立）
scripts/ tests/ docs/ deployment/ .servo/
```

完整说明：[docs/architecture/repo_structure_guide.md](docs/architecture/repo_structure_guide.md)

---

## 工作流程

```
选股池(X) × 模型(Y) × 配置(Z) → 全量扫荡 → 筛选 → 滚动IC验证 → 认证 → 推理 → 交易策略层
```

详见 [docs/architecture/xyz_test_matrix.md](docs/architecture/xyz_test_matrix.md)

---

## 快速开始

```bash
# 安装
conda env create -f environment.yml && conda activate py311-private
pip install -e ".[dev]"

# 最小回测
python scripts/run_backtest.py --symbols 600519,000333 --start 20220101 --end 20241231 --top-n 3

# 全量测试
pytest tests/
```

---

## 文档导航

| 目录 | 内容 |
|------|------|
| [docs/architecture/](docs/architecture/) | 架构设计：流水线、X×Y×Z 矩阵、模型注册表 |
| [docs/reference/](docs/reference/) | 接口契约：数据 schema、股票池 schema |
| [docs/guides/](docs/guides/) | 操作指南：选股池维护、模型维护、流水线运维 |
| [docs/research/](docs/research/) | 研究记录 |
| [docs/WORK_RULES.md](docs/WORK_RULES.md) | **全局工作规则（必读）** |
| [docs/README.md](docs/README.md) | 文档总导航 |

---

## 当前状态

- **Milestone**: MS-R2-001（Repo 目录排布重构）进行中
- **Pipeline**: ENV-000 → S0-001 → S1-001 → S2-001 → R0-001 → R1-001 → R2-001
- **pytest**: 395/397 pass
- **数据源**: TuShare（主）/ AkShare（备用）
- **环境**: py311-private
