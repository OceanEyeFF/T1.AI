# 生产环境调度器部署指南

本文档介绍如何在生产环境中部署 A-share Low-Frequency Lab 日频推荐流水线的自动化调度。

## 概述

日频流水线需要在每个交易日自动执行，完成以下任务：
1. 数据刷新（从 TuShare/AkShare 获取最新数据）
2. 推荐生成（使用 RecommendationEngine 生成多时间跨度推荐）
3. 持久化（保存到 SQLite 和 JSON/CSV/Markdown 文件）
4. 验证前日推荐（使用 RecommendationValidator 评估）
5. 监控与重训触发（检测模型性能退化）

本项目提供两种调度方案：
- **Cron**：轻量级，适合简单场景
- **Systemd Timer**：功能强大，适合需要高级管理的场景

## 前置准备

### 1. 环境依赖

```bash
# 确保 Python 3.10+ 已安装
python --version

# 创建虚拟环境（推荐）
cd /path/to/T1.AI
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 TuShare Token

```bash
# 方法 1: 环境变量（推荐）
export TUSHARE_TOKEN="your_tushare_token_here"

# 方法 2: 写入配置文件
echo "TUSHARE_TOKEN=your_token_here" > .env

# 方法 3: 直接修改 configs/data_source.yaml
# token: "your_token_here"
```

### 3. 验证流水线可执行

```bash
# 测试脚本语法
bash -n scripts/daily_pipeline.sh

# 手动运行一次（dry-run 模式）
./scripts/daily_pipeline.sh

# 检查日志
tail -f logs/pipeline.log
```

### 4. 创建必要目录

```bash
mkdir -p logs data/recommendations data/recommendations/validation
```

## 方案 1: Cron 调度

### 优点
- 配置简单，无需 root 权限
- 适合个人开发环境或小规模部署

### 缺点
- 缺少日志管理功能
- 无法方便地查看执行历史

### 部署步骤

#### 1. 编辑 crontab

```bash
# 打开 crontab 编辑器
crontab -e
```

#### 2. 添加调度任务

复制 `deployment/crontab.example` 中的内容，并根据实际路径修改：

```cron
# A-share Low-Frequency Lab Daily Pipeline
# 每个交易日下午 15:15 执行（A 股收盘后数据稳定）

# 设置 TuShare Token
TUSHARE_TOKEN=your_actual_token_here

# 日频流水线（周一至周五执行）
15 15 * * 1-5 cd /home/oceaneye/gitee/T1.AI && ./scripts/daily_pipeline.sh >> logs/cron.log 2>&1

# 周末清理临时文件（可选）
0 2 * * 6 find /home/oceaneye/gitee/T1.AI/data/cache -name "*.tmp" -mtime +7 -delete
```

**时间说明**：
- `15 15 * * 1-5`：周一至周五 15:15 执行
- A 股交易时间：9:30-11:30, 13:00-15:00
- 选择 15:15 是为了确保收盘数据已完全稳定

#### 3. 验证 crontab 配置

```bash
# 查看当前 crontab
crontab -l

# 测试立即执行（不等待定时）
./scripts/daily_pipeline.sh

# 检查日志
tail -f logs/cron.log
```

#### 4. 监控任务执行

```bash
# 查看 cron 系统日志
sudo tail -f /var/log/syslog | grep CRON

# 查看流水线日志
tail -f logs/pipeline.log

# 查看 cron 专用日志
tail -f logs/cron.log
```

### 常见问题排查

**问题 1: cron 任务未执行**
```bash
# 检查 cron 服务状态
sudo systemctl status cron

# 检查是否有语法错误
crontab -l

# 检查环境变量是否生效
15 15 * * 1-5 env > /tmp/cron-env.log 2>&1
```

**问题 2: 环境变量未生效**
- Cron 环境与 shell 环境不同，需在 crontab 中显式设置
- 或在 `daily_pipeline.sh` 中加载 `.env` 文件

**问题 3: 路径问题**
- 使用绝对路径，避免 `cd` 失败
- 示例：`/home/oceaneye/gitee/T1.AI/scripts/daily_pipeline.sh`

## 方案 2: Systemd Timer 调度

### 优点
- 完善的日志管理（journalctl）
- 可查看执行历史和状态
- 支持失败重试（可配置）
- 系统重启后自动恢复

### 缺点
- 需要 sudo 权限部署
- 配置相对复杂

### 部署步骤

#### 1. 复制 systemd 单元文件

```bash
# 复制到 systemd 用户目录（无需 sudo）
mkdir -p ~/.config/systemd/user
cp deployment/daily-pipeline.service ~/.config/systemd/user/
cp deployment/daily-pipeline.timer ~/.config/systemd/user/

# 或复制到系统目录（需要 sudo）
sudo cp deployment/daily-pipeline.service /etc/systemd/system/
sudo cp deployment/daily-pipeline.timer /etc/systemd/system/
```

#### 2. 修改配置文件

编辑 `~/.config/systemd/user/daily-pipeline.service`（或 `/etc/systemd/system/daily-pipeline.service`）：

```ini
[Service]
# 修改为实际用户
User=oceaneye

# 修改为实际项目路径
WorkingDirectory=/home/oceaneye/gitee/T1.AI
ExecStart=/home/oceaneye/gitee/T1.AI/scripts/daily_pipeline.sh

# 修改为实际 Token
Environment="TUSHARE_TOKEN=your_actual_token_here"

# 修改日志路径
StandardOutput=append:/home/oceaneye/gitee/T1.AI/logs/pipeline.log
StandardError=append:/home/oceaneye/gitee/T1.AI/logs/pipeline.log
```

#### 3. 启用并启动 Timer

```bash
# 用户级 systemd（无需 sudo）
systemctl --user daemon-reload
systemctl --user enable daily-pipeline.timer
systemctl --user start daily-pipeline.timer

# 系统级 systemd（需要 sudo）
sudo systemctl daemon-reload
sudo systemctl enable daily-pipeline.timer
sudo systemctl start daily-pipeline.timer
```

#### 4. 验证 Timer 状态

```bash
# 查看 timer 状态
systemctl --user status daily-pipeline.timer
# 或
sudo systemctl status daily-pipeline.timer

# 查看下次执行时间
systemctl --user list-timers daily-pipeline.timer
# 或
sudo systemctl list-timers daily-pipeline.timer

# 查看 service 状态
systemctl --user status daily-pipeline.service
# 或
sudo systemctl status daily-pipeline.service
```

#### 5. 手动触发执行（测试）

```bash
# 手动触发一次执行
systemctl --user start daily-pipeline.service
# 或
sudo systemctl start daily-pipeline.service

# 查看执行日志
journalctl --user -u daily-pipeline.service -f
# 或
sudo journalctl -u daily-pipeline.service -f
```

### 日志管理

```bash
# 查看最近 50 条日志
journalctl --user -u daily-pipeline.service -n 50
# 或
sudo journalctl -u daily-pipeline.service -n 50

# 实时查看日志
journalctl --user -u daily-pipeline.service -f
# 或
sudo journalctl -u daily-pipeline.service -f

# 查看指定日期的日志
journalctl --user -u daily-pipeline.service --since "2025-01-17"
# 或
sudo journalctl -u daily-pipeline.service --since "2025-01-17"

# 查看上次执行的日志
journalctl --user -u daily-pipeline.service -b 0
# 或
sudo journalctl -u daily-pipeline.service -b 0
```

### 停止和禁用

```bash
# 停止 timer
systemctl --user stop daily-pipeline.timer
# 或
sudo systemctl stop daily-pipeline.timer

# 禁用 timer（开机不自启）
systemctl --user disable daily-pipeline.timer
# 或
sudo systemctl disable daily-pipeline.timer
```

## 错误排查指南

### 1. 数据源问题

**症状**：日志显示 "TuShare API 调用失败" 或 "网络超时"

**排查步骤**：
```bash
# 检查 Token 是否正确
echo $TUSHARE_TOKEN

# 测试网络连接
ping api.tushare.pro

# 检查 API 配额
# 登录 TuShare 官网查看每日调用次数

# 查看错误日志
grep "ERROR" logs/pipeline.log
```

**解决方案**：
- 检查 TuShare Token 有效性
- 检查网络代理设置
- 降级使用缓存数据（配置 `allow_stale_data: true`）

### 2. 权限问题

**症状**：日志显示 "Permission denied" 或无法创建文件

**排查步骤**：
```bash
# 检查脚本权限
ls -l scripts/daily_pipeline.sh

# 检查目录权限
ls -ld data logs

# 检查文件所有者
stat data/recommendations.db
```

**解决方案**：
```bash
# 修复脚本权限
chmod +x scripts/daily_pipeline.sh

# 修复目录权限
chmod 755 data logs

# 修复所有者
chown -R oceaneye:oceaneye data logs
```

### 3. 虚拟环境问题

**症状**：日志显示 "ModuleNotFoundError" 或 "No module named ..."

**排查步骤**：
```bash
# 检查虚拟环境是否存在
ls -ld venv

# 检查 Python 路径
which python

# 检查依赖安装
pip list | grep torch
```

**解决方案**：
```bash
# 重新创建虚拟环境
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 内存/磁盘问题

**症状**：流水线执行到一半中断或日志显示 "Out of memory"

**排查步骤**：
```bash
# 检查内存使用
free -h

# 检查磁盘空间
df -h

# 检查流水线进程
ps aux | grep daily_pipeline
```

**解决方案**：
- 清理临时文件：`find data/cache -name "*.tmp" -delete`
- 减少推荐榜单数量（修改 `configs/pipeline.yaml` 中的 `default_top_n`）
- 配置 swap 分区

### 5. 模型加载问题

**症状**：日志显示 "Failed to load model checkpoint"

**排查步骤**：
```bash
# 检查模型文件是否存在
ls -lh models/latest_mtl.pt

# 检查文件完整性
file models/latest_mtl.pt

# 尝试手动加载模型
python -c "import torch; torch.load('models/latest_mtl.pt')"
```

**解决方案**：
- 重新训练模型：`python scripts/train_mtl.py`
- 使用备份模型（如果有）

## 监控建议

### 1. 日志告警

使用 `logwatch` 或自定义脚本监控错误日志：

```bash
# 检查失败执行
grep "Exit Code: [^0]" logs/pipeline.log

# 统计最近 7 天错误次数
grep "ERROR" logs/pipeline.log | grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l
```

### 2. 失败重试

修改 crontab 添加失败重试逻辑：

```cron
# 15:15 首次执行
15 15 * * 1-5 cd /path/to/T1.AI && ./scripts/daily_pipeline.sh || sleep 300 && ./scripts/daily_pipeline.sh
```

或在 systemd service 中添加：

```ini
[Service]
Restart=on-failure
RestartSec=300
```

### 3. 通知集成

#### Slack 通知示例

修改 `scripts/daily_pipeline.sh` 添加：

```bash
# 执行流水线
if ! python scripts/daily_pipeline.py --date "$TARGET_DATE" --config configs/pipeline.yaml; then
    # 失败时发送 Slack 通知
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"❌ Daily Pipeline Failed on '"$TARGET_DATE"'"}' \
        YOUR_SLACK_WEBHOOK_URL
fi
```

#### 邮件通知示例

```bash
# 失败时发送邮件
if [ $EXIT_CODE -ne 0 ]; then
    echo "Pipeline failed on $TARGET_DATE. Exit code: $EXIT_CODE" | \
        mail -s "Daily Pipeline Alert" your_email@example.com
fi
```

### 4. 性能监控

定期检查流水线执行时间：

```bash
# 提取执行时间
grep "execution_time_seconds" logs/pipeline.log | tail -n 10

# 统计平均执行时间
grep "execution_time_seconds" logs/pipeline.log | \
    awk -F': ' '{sum+=$2; count++} END {print "Average:", sum/count, "seconds"}'
```

## 最佳实践

1. **环境隔离**：始终使用虚拟环境，避免依赖冲突
2. **配置管理**：敏感信息（Token）使用环境变量，不要提交到版本控制
3. **日志轮转**：定期清理旧日志，避免磁盘占满
4. **备份策略**：定期备份 `data/recommendations.db` 和推荐文件
5. **监控告警**：配置失败通知，及时发现问题
6. **测试验证**：部署后手动触发一次执行，确保配置正确
7. **文档更新**：修改配置后及时更新文档

## 附录

### A. 日志轮转配置

创建 `/etc/logrotate.d/ashare-lab`：

```
/home/oceaneye/gitee/T1.AI/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 oceaneye oceaneye
}
```

### B. 环境变量配置文件

创建 `.env` 文件（不要提交到 git）：

```bash
# TuShare Token
TUSHARE_TOKEN=your_token_here

# Python 路径
PYTHONPATH=/home/oceaneye/gitee/T1.AI

# 可选：代理设置
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080
```

在 `daily_pipeline.sh` 中加载：

```bash
# 加载环境变量文件
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi
```

### C. 系统资源要求

**最低配置**：
- CPU: 2 核
- 内存: 4GB
- 磁盘: 10GB 可用空间

**推荐配置**：
- CPU: 4 核
- 内存: 8GB
- 磁盘: 50GB 可用空间（包含历史数据）

### D. 版本兼容性

- Python: 3.10+
- TuShare: 最新版本
- Systemd: 230+（支持 `Persistent=true`）
- Cron: 任意版本

## 联系支持

如遇问题，请检查：
1. 项目 README.md
2. GitHub Issues: https://github.com/yourusername/T1.AI/issues
3. 日志文件：`logs/pipeline.log`

---

**文档版本**：1.0
**更新日期**：2025-01-17
**维护者**：oceaneye
