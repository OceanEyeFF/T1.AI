# 日频流水线运维指南

> MS-R2-001 | 2026-06-23

## 入口

```bash
# 标准运行（使用当天日期）
python scripts/daily_pipeline.py

# 指定日期 + 自定义配置
python scripts/daily_pipeline.py --date 20250117 --config inputs/configs/pipeline.toml

# 干跑模式（只检查不执行）
python scripts/daily_pipeline.py --date 20250117 --dry-run
```

## 配置文件

| 文件 | 内容 |
|------|------|
| `inputs/configs/pipeline.toml` | 流水线参数（推荐目录、DB路径、日志） |
| `inputs/configs/data_source.toml` | 数据源选择（akshare / tushare / odp） |

## 输出位置

| 产物 | 路径 |
|------|------|
| 每日推荐 | `outputs/predictions/{date}.json` |
| 推荐 CSV | `outputs/predictions/{date}_{horizon}d.csv` |
| 推荐 Markdown | `outputs/predictions/{date}.md` |
| 验证报告 | `outputs/reports/` |
| 运行日志 | `workspace/runs/pipeline.log` |
| 运行元数据 | `workspace/runs/pipeline_runs.jsonl` |
| 推荐数据库 | `outputs/recommendations.db` |

## 部署

systemd timer 配置在 `deployment/daily-pipeline.timer`，每个交易日下午 15:15 触发。

```bash
# 安装
sudo cp deployment/daily-pipeline.service /etc/systemd/system/
sudo cp deployment/daily-pipeline.timer /etc/systemd/system/
sudo systemctl enable daily-pipeline.timer
sudo systemctl start daily-pipeline.timer

# 查看状态
systemctl status daily-pipeline.timer
journalctl -u daily-pipeline.service
```

## 监控

`configs/pipeline.yaml` 中的 monitoring 段（迁移后路径 TBD）：

- `rolling_window_days: 20` — 滚动窗口天数
- `horizon: 5` — 监控 horizon
- `ic_threshold: 0.04` — IC 告警阈值
- `retrain_trigger_mode: auto` — 自动重训触发
