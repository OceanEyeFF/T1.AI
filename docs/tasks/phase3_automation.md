# Phase 3: 自动化与生产化

**预计工作量：** 2-3天
**优先级：** ⭐⭐ 中高
**目标：** 实现每日自动化流程，无人工干预自动运行

---

## 任务概览

| 任务ID | 任务名称 | 预计时间 | 依赖 | 状态 |
|--------|---------|---------|------|------|
| 3.1 | 每日Pipeline脚本 | 1天 | Phase 1, Phase 2 | 🔲 待开始 |
| 3.2 | 增量训练自动化 | 1天 | 3.1 | 🔲 待开始 |
| 3.3 | Cron定时任务配置 | 0.5天 | 3.1, 3.2 | 🔲 待开始 |
| 3.4 | 模型监控与重训练 | 0.5天 | 3.2 | 🔲 待开始 |

---

## 任务3.1：每日Pipeline脚本 ⭐⭐⭐

**目标：** 实现完整的每日自动化流程

### 交付物

- `scripts/daily_pipeline.py` - 每日完整流程脚本
- `configs/data_source.yaml` - 数据源配置文件
- 流程日志（记录每日执行状态）

### 详细任务

#### 3.1.1 创建数据源配置文件

**代码位置：** `configs/data_source.yaml`

```yaml
# TuShare配置
tushare:
  token: ${TUSHARE_TOKEN}  # 从环境变量读取
  cache_dir: "data/cache"
  adjust: "qfq"            # 前复权
  retry: 3                 # 重试次数
  backoff_base: 0.5        # 退避基数（秒）

# 股票池配置
universe:
  exclude_st: true         # 排除ST股票
  exclude_star: true       # 排除科创板（688xxx）
  exclude_chinext: true    # 排除创业板（300xxx, 301xxx）
  exclude_bse: true        # 排除北交所（8xxx, 4xxx）
  min_price: 1.0           # 最低价格（元）
  min_volume: 1000         # 最低成交量（手）

# 特征配置
features:
  momentum:
    windows: [1, 5, 20]
  technical:
    rsi_period: 14
    macd_short: 12
    macd_long: 26
    macd_signal: 9
    bollinger_window: 20
  volume:
    ratio_window: 5
  price_slope:
    windows: [10, 20]

# 标签配置
labels:
  horizons: [3, 5, 10]
  handle_missing: "mask"   # NaN掩码

# 输出配置
output:
  recommendations_dir: "output/recommendations"
  validations_dir: "output/validations"
  reports_dir: "output/reports"
  models_dir: "models"
```

#### 3.1.2 创建每日Pipeline脚本

**代码位置：** `scripts/daily_pipeline.py`

**核心流程：**
```python
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path

from ashare_lab.data.tushare_source import load_or_fetch_daily_bars
from ashare_lab.recommendation.engine import RecommendationEngine
from ashare_lab.recommendation.validator import RecommendationValidator
from ashare_lab.recommendation.history import RecommendationHistory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/daily_pipeline.log"),
        logging.StreamHandler(),
    ]
)

def main(config_path: str = "configs/data_source.yaml"):
    """每日完整自动化流程"""
    logger = logging.getLogger(__name__)
    today = datetime.now().strftime("%Y%m%d")

    logger.info(f"{'='*60}")
    logger.info(f"每日Pipeline开始执行 - {today}")
    logger.info(f"{'='*60}")

    # Step 1: 加载配置
    logger.info("Step 1: 加载配置文件")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Step 2: TuShare增量拉取（仅拉取今日数据）
    logger.info("Step 2: TuShare增量拉取今日数据")
    try:
        fetch_incremental_data(today, config)
        logger.info("  ✅ 数据拉取成功")
    except Exception as e:
        logger.error(f"  ❌ 数据拉取失败: {e}")
        return

    # Step 3: 特征计算（滚动30日窗口）
    logger.info("Step 3: 计算特征（滚动30日窗口）")
    try:
        features = compute_features(today, config)
        logger.info(f"  ✅ 特征计算完成，共 {features.shape[1]} 个特征")
    except Exception as e:
        logger.error(f"  ❌ 特征计算失败: {e}")
        return

    # Step 4: 标签计算
    logger.info("Step 4: 计算标签（3D/5D/10D）")
    try:
        labels = compute_labels(today, config)
        logger.info("  ✅ 标签计算完成")
    except Exception as e:
        logger.error(f"  ❌ 标签计算失败: {e}")
        return

    # Step 5: 增量训练（可选，根据配置决定）
    if should_run_incremental_training(today):
        logger.info("Step 5: 增量训练模型")
        try:
            incremental_training(features, labels, config)
            logger.info("  ✅ 增量训练完成")
        except Exception as e:
            logger.error(f"  ❌ 增量训练失败: {e}")
            return
    else:
        logger.info("Step 5: 跳过增量训练（非训练日）")

    # Step 6: 生成推荐榜单
    logger.info("Step 6: 生成推荐榜单（3×Top-10）")
    try:
        recommendations = generate_recommendations(today, config)
        logger.info("  ✅ 推荐榜单生成成功")

        # 保存推荐结果
        save_recommendations(today, recommendations, config)
        logger.info(f"  ✅ 推荐结果已保存: output/recommendations/{today}.json")
    except Exception as e:
        logger.error(f"  ❌ 推荐生成失败: {e}")
        return

    # Step 7: 验证前一日推荐（如果存在）
    yesterday = get_previous_trading_day(today)
    if yesterday_recommendation_exists(yesterday):
        logger.info(f"Step 7: 验证前一日推荐（{yesterday}）")
        try:
            validation_results = validate_yesterday_recommendations(
                yesterday, today, config
            )
            logger.info("  ✅ 验证完成")

            # 打印验证结果
            for horizon, result in validation_results.items():
                logger.info(f"    {horizon}: 命中率={result.hit_rate:.1%}, "
                          f"IC={result.ic:.4f}, 超额收益={result.excess_return:.2%}")

            # 保存验证结果
            save_validation_results(yesterday, validation_results, config)
        except Exception as e:
            logger.error(f"  ❌ 验证失败: {e}")
    else:
        logger.info("Step 7: 无前一日推荐，跳过验证")

    # Step 8: 模型监控（IC衰减检测）
    logger.info("Step 8: 模型性能监控")
    try:
        check_model_performance(config)
        logger.info("  ✅ 模型监控完成")
    except Exception as e:
        logger.error(f"  ❌ 模型监控失败: {e}")

    logger.info(f"{'='*60}")
    logger.info(f"每日Pipeline执行完成 - {today}")
    logger.info(f"{'='*60}")

# ========== 辅助函数 ==========

def fetch_incremental_data(date: str, config: dict):
    """增量拉取今日数据"""
    # 实现数据拉取逻辑
    pass

def compute_features(date: str, config: dict):
    """计算特征"""
    # 实现特征计算逻辑
    pass

def compute_labels(date: str, config: dict):
    """计算标签"""
    # 实现标签计算逻辑
    pass

def should_run_incremental_training(date: str) -> bool:
    """判断是否需要增量训练（例如：每周五训练）"""
    weekday = datetime.strptime(date, "%Y%m%d").weekday()
    return weekday == 4  # 周五（0=周一, 4=周五）

def incremental_training(features, labels, config):
    """增量训练"""
    # 实现增量训练逻辑
    pass

def generate_recommendations(date: str, config: dict):
    """生成推荐"""
    # 实现推荐生成逻辑
    pass

def save_recommendations(date: str, recommendations: dict, config: dict):
    """保存推荐结果"""
    # 实现保存逻辑
    pass

def get_previous_trading_day(date: str) -> str:
    """获取前一交易日"""
    # 实现交易日历逻辑
    pass

def yesterday_recommendation_exists(date: str) -> bool:
    """检查前一日推荐是否存在"""
    return Path(f"output/recommendations/{date}.json").exists()

def validate_yesterday_recommendations(
    yesterday: str, today: str, config: dict
):
    """验证前一日推荐"""
    # 实现验证逻辑
    pass

def save_validation_results(date: str, results: dict, config: dict):
    """保存验证结果"""
    # 实现保存逻辑
    pass

def check_model_performance(config: dict):
    """模型性能监控"""
    # 实现监控逻辑
    pass

if __name__ == "__main__":
    main()
```

**验收标准：**
- ✅ Pipeline成功运行（无报错）
- ✅ 自动完成：数据拉取 → 特征计算 → 推荐生成 → 验证
- ✅ 日志完整（记录每个步骤执行状态）

---

## 任务3.2：增量训练自动化 ⭐⭐⭐

**目标：** 实现自动化增量训练，集成到每日Pipeline

### 交付物

- 增量训练逻辑（集成在daily_pipeline.py中）
- 增量训练配置（configs/model_mtl.yaml）

### 详细任务

#### 3.2.1 扩展模型配置文件

**代码位置：** `configs/model_mtl.yaml`（追加以下内容）

```yaml
# 增量训练配置
incremental:
  enabled: true
  frequency: "weekly"       # 训练频率：daily/weekly/monthly
  weekday: 4                # 如果是weekly，则在周五训练（0=周一）
  freeze_layers: 2          # 冻结前N层
  learning_rate: 1e-5       # 增量训练学习率（小学习率）
  max_epochs: 2             # 增量训练轮数（快速微调）
  data_window: 30           # 训练数据窗口（最近30日）
  valid_window: 7           # 验证数据窗口（最近7日）
  min_ic_threshold: 0.04    # 最低IC阈值（低于此值触发完整重训练）
```

#### 3.2.2 实现增量训练逻辑

**集成位置：** `scripts/daily_pipeline.py`（函数：`incremental_training`）

**核心流程：**
```python
def incremental_training(features, labels, config):
    """增量训练流程"""
    logger = logging.getLogger(__name__)

    # Step 1: 加载最近checkpoint
    model_path = Path(config["output"]["models_dir"]) / "latest.pt"
    if not model_path.exists():
        logger.warning("  ⚠️ 未找到checkpoint，跳过增量训练")
        return

    model = create_mtl_model(...)
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint["model_state_dict"])

    logger.info(f"  已加载checkpoint: {model_path}")

    # Step 2: 冻结前K层
    freeze_layers = config["incremental"]["freeze_layers"]
    freeze_encoder_layers(model, num_layers=freeze_layers)
    logger.info(f"  已冻结前{freeze_layers}层编码器")

    # Step 3: 构建训练数据（最近30日）
    window = config["incremental"]["data_window"]
    train_data = build_recent_dataset(features, labels, window=window)

    valid_window = config["incremental"]["valid_window"]
    valid_data = build_recent_dataset(features, labels, window=valid_window)

    # Step 4: 增量训练（1-2 epoch）
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["incremental"]["learning_rate"],
    )

    max_epochs = config["incremental"]["max_epochs"]
    for epoch in range(max_epochs):
        train_loss = train_epoch(model, train_data, optimizer)
        val_loss, val_ic = validate_epoch(model, valid_data)

        logger.info(f"    Epoch {epoch+1}/{max_epochs}: "
                   f"Train Loss={train_loss:.4f}, "
                   f"Valid Loss={val_loss:.4f}, IC={val_ic:.4f}")

    # Step 5: 保存新checkpoint
    torch.save({
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_ic": val_ic,
        "timestamp": datetime.now().isoformat(),
    }, model_path)

    logger.info(f"  ✅ 新checkpoint已保存")

    # Step 6: IC衰减检测
    if val_ic < config["incremental"]["min_ic_threshold"]:
        logger.warning(f"  ⚠️ IC={val_ic:.4f} < 阈值 "
                      f"{config['incremental']['min_ic_threshold']:.4f}")
        logger.warning("  建议触发完整重训练！")
```

**验收标准：**
- ✅ 增量训练成功执行（1-2 epoch）
- ✅ 模型checkpoint更新
- ✅ 验证集IC保持在合理范围（> 0.04）

---

## 任务3.3：Cron定时任务配置 ⭐⭐

**目标：** 配置Cron定时任务，每日自动运行Pipeline

### 交付物

- Cron配置文件（`configs/cron_job.sh`）
- 部署文档（`docs/deployment.md`）

### 详细任务

#### 3.3.1 创建Cron配置脚本

**代码位置：** `configs/cron_job.sh`

```bash
#!/bin/bash

# 每日Pipeline自动化脚本
# 运行时间：每个工作日 15:15

# 设置环境变量
export TUSHARE_TOKEN="your_tushare_token_here"
export PYTHONPATH="/home/user/T1.AI/src:$PYTHONPATH"

# 激活虚拟环境
source /home/user/T1.AI/venv/bin/activate

# 进入项目目录
cd /home/user/T1.AI

# 运行每日Pipeline
python scripts/daily_pipeline.py >> logs/cron_$(date +\%Y\%m\%d).log 2>&1

# 检查执行状态
if [ $? -eq 0 ]; then
    echo "$(date): Daily pipeline executed successfully" >> logs/cron_status.log
else
    echo "$(date): Daily pipeline FAILED" >> logs/cron_status.log
    # 可选：发送邮件通知
    # echo "Daily pipeline failed" | mail -s "Pipeline Error" your@email.com
fi
```

#### 3.3.2 配置Crontab

**步骤：**

1. 编辑crontab：
   ```bash
   crontab -e
   ```

2. 添加定时任务（每个工作日15:15执行）：
   ```cron
   # 每日Pipeline - 工作日15:15执行
   15 15 * * 1-5 /home/user/T1.AI/configs/cron_job.sh
   ```

3. 验证crontab：
   ```bash
   crontab -l
   ```

#### 3.3.3 创建部署文档

**代码位置：** `docs/deployment.md`

```markdown
# 部署文档

## 环境准备

1. 安装Python依赖：
   ```bash
   python -m pip install -e ".[dev]"
   ```

2. 设置环境变量：
   ```bash
   export TUSHARE_TOKEN="your_token_here"
   ```

3. 创建必要目录：
   ```bash
   mkdir -p logs output/{recommendations,validations,reports} models
   ```

## Cron定时任务配置

1. 修改 `configs/cron_job.sh` 中的路径和Token
2. 添加执行权限：
   ```bash
   chmod +x configs/cron_job.sh
   ```
3. 配置crontab（见上文）

## 手动测试

首次部署前，手动运行Pipeline验证：
```bash
python scripts/daily_pipeline.py
```

检查日志：
```bash
tail -f logs/daily_pipeline.log
```

## 监控与维护

- 每日检查日志：`logs/daily_pipeline.log`
- 每周检查模型IC：`logs/cron_status.log`
- 每月检查推荐命中率：运行 `scripts/evaluate_recommendation.py`
```

**验收标准：**
- ✅ Cron任务成功配置
- ✅ 手动测试通过（Pipeline成功运行）
- ✅ 部署文档完整

---

## 任务3.4：模型监控与重训练 ⭐⭐

**目标：** 实现模型性能监控，自动触发重训练

### 交付物

- `src/ashare_lab/monitoring/model_monitor.py` - 模型监控模块
- IC衰减检测逻辑（集成在daily_pipeline.py中）

### 详细任务

#### 3.4.1 创建模型监控模块

**代码位置：** `src/ashare_lab/monitoring/model_monitor.py`

```python
import logging
from pathlib import Path
import pandas as pd

class ModelMonitor:
    def __init__(self, history_db_path: str):
        self.history = RecommendationHistory(history_db_path)
        self.logger = logging.getLogger(__name__)

    def check_ic_decay(
        self,
        window: int = 30,
        threshold: float = 0.04,
    ) -> dict:
        """
        检测IC衰减

        Args:
            window: 滚动窗口（默认30日）
            threshold: IC阈值（默认0.04）

        Returns:
            {
                "3d": {"avg_ic": ..., "needs_retrain": bool},
                "5d": {...},
                "10d": {...},
            }
        """
        results = {}

        # 获取最近30日的验证结果
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=window)).strftime("%Y%m%d")

        for horizon in ["3d", "5d", "10d"]:
            # 查询历史IC
            validations = self.history.query_validations(
                start_date, end_date, horizon
            )

            if len(validations) < 5:
                self.logger.warning(f"  {horizon}: 历史数据不足，跳过监控")
                results[horizon] = {"avg_ic": None, "needs_retrain": False}
                continue

            # 计算平均IC
            avg_ic = validations["ic"].mean()

            # 判断是否需要重训练
            needs_retrain = avg_ic < threshold

            results[horizon] = {
                "avg_ic": avg_ic,
                "needs_retrain": needs_retrain,
            }

            if needs_retrain:
                self.logger.warning(
                    f"  ⚠️ {horizon}: 平均IC={avg_ic:.4f} < 阈值{threshold:.4f}，"
                    f"建议重训练！"
                )
            else:
                self.logger.info(
                    f"  ✅ {horizon}: 平均IC={avg_ic:.4f}，性能正常"
                )

        return results

    def trigger_full_retrain(self):
        """触发完整重训练（占位函数）"""
        self.logger.warning("  🔄 触发完整重训练...")
        # 实现完整重训练逻辑（例如：调用 scripts/train_mtl.py）
        # subprocess.run(["python", "scripts/train_mtl.py"])
        pass
```

#### 3.4.2 集成到每日Pipeline

**代码位置：** `scripts/daily_pipeline.py`（函数：`check_model_performance`）

```python
def check_model_performance(config: dict):
    """模型性能监控"""
    logger = logging.getLogger(__name__)

    monitor = ModelMonitor("data/recommendation_history.db")

    # 检测IC衰减
    results = monitor.check_ic_decay(
        window=30,
        threshold=config["incremental"]["min_ic_threshold"],
    )

    # 判断是否需要完整重训练
    any_needs_retrain = any(r["needs_retrain"] for r in results.values() if r)

    if any_needs_retrain:
        logger.warning("  ⚠️ 检测到IC显著衰减，建议触发完整重训练！")
        # monitor.trigger_full_retrain()  # 可选：自动触发
    else:
        logger.info("  ✅ 模型性能稳定，无需重训练")
```

**验收标准：**
- ✅ IC衰减检测成功运行
- ✅ 低于阈值时发出警告
- ✅ 日志记录完整

---

## Phase 3 总体验收标准

### 功能验收

- ✅ 每日Pipeline成功运行（数据拉取 → 推荐 → 验证 → 监控）
- ✅ 增量训练自动执行（每周一次）
- ✅ Cron定时任务正常触发（工作日15:15）
- ✅ 模型监控IC衰减检测正常

### 稳定性验证

- ✅ 连续运行3日无报错
- ✅ 日志完整（每日自动记录）
- ✅ 推荐结果正常保存

### 性能验证

- ✅ 单次Pipeline执行时间 < 10分钟
- ✅ 增量训练时间 < 5分钟
- ✅ IC保持在合理范围（> 0.04）

---

## 总结

完成Phase 3后，整个**多时间跨度股票推荐系统**即可投入生产使用！🎉

### 系统能力清单 ✅

- ✅ 每日自动生成3×Top-10推荐榜单
- ✅ 自动验证前一日推荐准确性
- ✅ 每周自动增量训练更新模型
- ✅ 自动监控模型性能（IC衰减检测）
- ✅ 完整日志记录与月度报告

### 下一步优化方向 💡

1. **Web可视化界面**（查看推荐榜单和历史表现）
2. **微信/邮件通知**（每日推送推荐结果）
3. **多模型Ensemble**（集成LSTM + Transformer）
4. **基本面特征扩展**（财报数据、行业分类）
5. **行业中性化**（避免推荐集中在单一行业）
