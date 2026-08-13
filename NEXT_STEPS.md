# 下一步工作安排（Next Steps）

> 2026-08-13 | 双路 CodeReview 修复后 | 本文档是唯一执行入口，任务按编号逐项推进

## 当前状态

项目已完成 R2（三区布局）→ R3（旧文件清理）→ T1（测试体系）→ R4（TuShare 数据湖合同）。
2026-08 完成换机后的环境重建、akshare 移除、双路 CodeReview 与 P0 缺陷修复：

- **环境**：`py311-private`（Python 3.11 + PyTorch cu130，RTX 3080 Ti GPU 可用）
- **数据源**：TuShare 单一信源（akshare 已完全移除，含负向合同测试）
- **测试**：1020 passed / 10 skipped，覆盖率 77.13%（门禁 76）
- **数据湖**：R4 合同冻结，但 `inputs/data/cache` **尚未落盘**（P0-①）
- **选股池**：`custom_research_liquidity_quality_v1`（61 只，research_only）已注册

## 执行纪律

- 每个任务**独立提交**，提交前全量测试 + 覆盖率不回退
- 债务类任务（D*）**禁止与功能改动混合提交**
- 每完成一个任务，更新本文档勾选状态并标注日期
- 提交/推送须经程序员批准（docs/WORK_RULES.md）

---

# P0 执行清单：把主线预测做"可信"

## 阶段 0 — 穿插性基础任务（与主线并行，可随时穿插）

### ☐ T0-A [D6] 本地噪音清理（~10 分钟）
- 删除 gitignored 历史文档 `.claude/specs/`、`.autoworkflow/`（含 akshare/旧路径字样，仅本机噪音）
- 验收：`git status` 无变化；本机目录已清

### ☐ T0-B [D1] 配置格式统一：真 TOML（~半天）
1. `inputs/configs/{pipeline,data_source}.toml` + `profiles/model_mtl.toml` 由 YAML 内容转真 TOML
2. `scripts/daily_pipeline.py:_load_yaml` → tomllib；`scripts/train_mtl.py` yaml.safe_load → tomllib
3. 新增合同测试：`inputs/configs/**/*.toml` 全部可被 `tomllib.loads` 解析
4. `test_model_mtl_yaml_parses` 改名/改实现
- 验收：全量绿 + grep 确认无 yaml 解析 .toml + `daily_pipeline --dry-run`、`train_mtl --dry-run` 通过

### ☐ T0-C [D4-A] ruff 机械批（~2 小时）
- `ruff check --fix --select I001,B009,UP006,PLR0402`；RUF100 逐条复核 noqa 是否仍必要
- 验收：该批规则计数归零、全量绿（独立提交）

### ☐ T0-D [D5] 测试深度补强（~2 小时）
1. validator 适配器测试 `assert_has_calls` 锁定 source/adjust/token/refresh/调用次数与顺序
2. `test_infra_a_flow` 改真实 `load_or_fetch_daily_bars` 消费 fixture（不再内联重实现）
3. 动态 fixture 增加明确的交易日缺口用例（周末缺口）
- 验收：全量绿（独立提交）

### ☐ T0-E [D4-B] ruff 手动批（~3 小时）
- F401（确认无副作用导入）/UP035/RUF046/SIM118/FLY002/SIM102 逐文件小修
- 验收：该批计数归零、全量绿（独立提交）

### ☐ T0-F [D4-C] ruff 语义批（~2 小时，与 P0-④ 联动）
- BLE001/TRY004/DTZ005/DTZ007 逐处评审；先明确时区约定（建议：naive 北京时间 + 注释或 per-file-ignores）
- 验收：剩余项全部有明确 noqa 理由；全量绿（独立提交）

### ☐ T0-G [D3] deployment install.sh 模板化（~1 小时，下次换机/部署前完成即可）
1. service 路径改 `PROJECT_ROOT` 占位符；新增 `deployment/install.sh`（接收部署机路径 sed 替换 + TUSHARE_TOKEN 非占位校验）
2. `test_deployment_files.py` 锁定占位符机制；ops 文档补充 install.sh 用法
- 验收：换路径部署只需跑 install.sh；测试锁定

---

## 阶段 1 — P0-① 数据湖落盘（批准池 61 只 limited-live）

### ☐ 1.1 限流与权限确认（~15 分钟）
- 核对 TUSHARE_TOKEN 积分等级；`pro.query` 验证 daily/qfq/daily_basic/moneyflow/index_daily 权限
- 记录限流上限（`inputs/configs/tushare_rate_limits.toml` L2 caps）
- 验收：权限清单记录在案；无权限接口提前降级

### ☐ 1.2 锚点验证（~20 分钟）
- 510300.SH 小窗口（近 30 交易日）拉取 daily/qfq/daily_basic/moneyflow 全链路
- 重点观察 pandas 3.0.5 兼容性、列名、复权值合理性
- 验收：锚点数据落盘 `inputs/data/cache/tushare_qfq/510300.SH/`，schema 符合 R4 合同

### ☐ 1.3 全池 qfq 日线拉取（~1-2 小时，受限流支配）
- 61 只 × 2023-01-01 起，分批（每批 ≤10 只）+ 断点续传（复用 r4_batch_resume 机制）
- 拉取后逐只校验：行数、日期窗口、NaN 比例
- 验收：61/61 落盘，缺口清单输出

### ☐ 1.4 daily_basic + moneyflow 拉取（~1-2 小时）
- 同池同窗口，同样分批断点
- 验收：61/61 落盘，与 qfq 分区对齐

### ☐ 1.5 落盘 QA 与 manifest（~30 分钟）
- 分区行数、日期覆盖、缺洞清单汇总；写入 workspace 记录
- 验收：`make_r4_datalake` 对全池读取通过（cache-first，不触网）

## 阶段 2 — P0-② 合同测试恢复与增强 [D2]（紧随 1.5，~2 小时）

### ☐ 2.1 skip → 硬断言
- `test_r4_cache_schema_contract.py` 移除 cache 缺失 skip（落盘后 10 skip → 10 pass）
- 验收：10 项真实通过

### ☐ 2.2 深度增强
- 遍历全部 symbols/parts；锁定历史起点（≈2023-01 首个交易日，合理容差）与连续性；manifest 与分区文件集合交叉校验
- 验收：人为注入 schema 漂移/缺数可被拦截

### ☐ 2.3 与 committed fixture 合同互补
- 确认 `test_seeded_cache_schema.py`（永不 skip）与真实湖合同（落盘后硬断言）双层防护成立
- 验收：双层测试均绿

## 阶段 3 — P0-③ 评估范式固化（~1 天）

### ☐ 3.1 Daily-CS IC/RankIC 基线复跑
- 用落盘数据跑现有 daily_cs pipeline，产出基线数字
- 验收：基线报告入 `outputs/reports/`，命令可重复执行

### ☐ 3.2 月胜率分布 + trade-like Top-N 面板
- 补充月度胜率分布统计与 trade-like panel 评估
- 验收：两个评估脚本可用且产出可对比报告

### ☐ 3.3 评估门禁协议执行版
- `docs/research/mainline_3510d_evaluation_gate_protocol.md` 更新为可执行门禁（阈值/命令/产物清单）
- 验收：文档命令可照抄执行

## 阶段 4 — P0-④ 伪信号系统性排查（~2 天）

### ☐ 4.1 标签起点对齐审计
- 验证标签起点 t close → t+1 open 全链路无错位（含 1d 标签）
- 验收：审计报告 + 错位修复项

### ☐ 4.2 sanity checks 三件套
- shuffle / time-reverse / lag-1 对照实验，主信号必须显著优于随机
- 验收：三项实验报告，不达标则排查原因

### ☐ 4.3 复权/停牌/涨跌停处理审计
- qfq 口径一致性、停牌期处理、涨跌停对标签的影响
- 验收：审计报告 + 处理策略决策记录

## 阶段 5 — P0-⑤ 模型同窗比较（~2 天）

### ☐ 5.1 LSTM / XGBoost 同窗同标签训练
- 同一窗口、同一标签、同一数据集训练两模型
- 验收：训练日志与 checkpoint 落盘

### ☐ 5.2 IC/收益一致性结论
- 两模型 IC、RankIC、面板收益对比；主模型选择结论
- 验收：结论报告；`workspace/registry/certified.json` 落第一个认证记录或明确否决理由

---

## P1（阶段 5 通过后）：主线性信号优化

1. 窗口长度、重训频率、loss 权重实验
2. `pred_3d/pred_5d/pred_10d → alpha_score` 聚合契约固化
3. 认证模型配对 → `workspace/registry/certified.json`

## P2（后续）：扩展

1. `1d` 分钟级数据可用性验证
2. 决策模型 I/O 协议冻结
3. 生产调度监控（deployment 全链路 + T0-G 落地）

## 当前明确不做

- 不把 `1d` 并入主线打分
- 不用日 K-only 给 `1d` 下最终结论
- 不在主线通过可信门禁前做复杂决策逻辑
- 不上新闻/公告/事件 embedding

---

## 关联文档

- 长期路线：[ROADMAP.md](ROADMAP.md)
- 全局工作规则：[docs/WORK_RULES.md](docs/WORK_RULES.md)
- 文档总导航：[docs/README.md](docs/README.md)
- 主线评估门禁：[docs/research/mainline_3510d_evaluation_gate_protocol.md](docs/research/mainline_3510d_evaluation_gate_protocol.md)
- Daily-CS 工作流：[docs/research/daily_cs_eval_workflow.md](docs/research/daily_cs_eval_workflow.md)
- 研究清单：[docs/research/research_checklist.md](docs/research/research_checklist.md)
