# T1.AI 本地数据运维

在 Ubuntu WSL 的仓库根目录运行，使用 `py311-private` 环境。采集从环境变量或仓库的私有 `.env` 读取 `TUSHARE_TOKEN`。状态检查、账户回放和恢复均可离线运行。

## 日常检查

```bash
conda activate py311-private
python -m scripts.data_ops status
python -m scripts.data_ops daily --dry-run
python -m scripts.data_ops daily --symbol 600519.SH
python -m scripts.data_ops daily
```

| 数据 | 存放位置 | 检查方式 |
|---|---|---|
| A 股行情、每日指标、资金流和 ETF 锚点 | `inputs/data/cache/` | 按 R4 股票池和 SSE 交易日历列出各标的缺行日期。指标和资金流以对应股票有日线的交易日为准。 |
| 外部九条日线 | `inputs/data/cache/tushare_external/daily.sqlite` | 检查各序列最近交易日和观察时间。决策回放仍用带时区的时点查询。 |
| 人工账户 | `inputs/data/private/broker/<alias>/` 和 `workspace/runs/account_replay/<alias>/ledger.sqlite` | 检查导入批次、最近快照和对应批次的对账状态。 |
| 研究与认证 | `workspace/datasets/`、Feature Contract 和认证注册表 | 检查数据集元数据摘要、特征契约版本和模型认证状态。 |

定时运行只采集到北京时间的前一天，外部行情仍按来源市场排除当地当天。dry-run 用本地交易日历估算各接口调用量，未覆盖日期按工作日估算。低于 3 GiB 显示容量告警，低于 2 GiB 阻止采集写入。补采更新前复权历史会先检查旧交易日与本次复权因子，所有年份校验完成后切换分区。

采集清单在 `workspace/runs/data_ops/<id>/manifest.json`，最近一次可从 `status` 查看。退出码 `0` 表示通过，`1` 表示存在待核查缺行或运行错误，`2` 表示写入条件受阻。失败时先看 `errors` 与 `resume`，再运行一次 `daily`。续跑根据已写入的分区和已检查的缺口重新规划。供应端限流解除后再执行。采集用 TuShare [停复牌记录](https://tushare.pro/document/2?doc_id=214)核对 A 股缺失日线，已确认的全天停牌日期单列在 `suspended_dates`，其余缺行保留在 `missing_dates`。最近三个交易日的缺行会继续复查。外部缓存依照实际观察时间保存修订，重复拉取同一值不增加版本。

## 券商对账

```bash
python -m scripts.data_ops replay-demo
```

演练将两套模拟 CSV 导入 `demo-cn` 和 `demo-hk`，重复导入确认批次未变，再各用独立期末快照核对。每次回放生成一份新报告，包含每笔卖出的 FIFO 成本、手续费、区间盈亏，以及人工决策时可见的外部行情。模拟估值价格标记为 `synthetic`。

真实账户使用本地别名，将原件和标准化副本保留在对应的私有输入目录。继续通过 `scripts.account_replay import` 手工导入并指定 `--market CN` 或 `--market HK`。回放时将 `--out-dir` 指向 `outputs/reports/account_replay/<alias>/<run>`，并提供带来源说明的非复权估值价格。账户报表分别以 CNY 和 HKD 列示。具体 CSV 字段和导入顺序见[账户回放说明](../architecture/account_replay_mvp.md)。

## 备份和恢复演练

```bash
drill_dir=$(mktemp -d)
python -m scripts.data_ops backup --dest "$drill_dir/backup"
python -m scripts.data_ops restore --source "$drill_dir/backup" --dest "$drill_dir/restored"
python -m scripts.data_ops --root "$drill_dir/restored" status
python -m scripts.data_ops --root "$drill_dir/restored" replay-demo
python -m scripts.external_daily --cache-dir "$drill_dir/restored/inputs/data/cache" \
  replay --market HK --as-of '2026-11-24T10:00:00+08:00'
```

备份记录文件 SHA-256，SQLite 使用一致性快照。恢复在验完校验和与 SQLite 完整性后才发布到目标空目录。备份包括当前行情缓存、有规范账本路径的账户私有输入与账本、运维及对账清单、研究元数据和认证配置。数据集和模型权重按研究流程重建，凭据需在恢复环境单独配置。备份可能含真实券商原件，应使用当前用户独占的本地目录。演练期间暂停手工改写券商原件。

## Windows 定时任务

从仓库根目录打开 Windows PowerShell，使用实际 WSL 用户、路径和 Conda Python 注册。任务以当前 Windows 用户运行，每天北京时间 14:30 启动，错过按任务计划程序的规则补跑。该配置以用户已登录为前提。

```powershell
.\deployment\register-data-ops.ps1 -Distribution Ubuntu -WslUser oceaneye `
  -WslRepo /mnt/e/repos/WSL/personal/T1.AI `
  -WslPython /home/oceaneye/miniconda3/envs/py311-private/bin/python
Start-ScheduledTask -TaskName 'T1.AI-DataOps'
Get-ScheduledTaskInfo -TaskName 'T1.AI-DataOps'
```

任务结束后对照 `LastTaskResult` 和最新采集清单。Windows 启动或 WSL 失败可检查 `workspace/runs/data_ops/task.log`。暂停调度可使用 `Disable-ScheduledTask -TaskName 'T1.AI-DataOps'`。
