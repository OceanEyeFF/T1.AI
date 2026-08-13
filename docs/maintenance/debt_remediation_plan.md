# 残余债务修复规划（Debt Remediation Plan）

> 2026-08-13 | 双路 CodeReview（CodeX gpt-5.6-sol + Pi deepseek-v4-pro）收尾输出
> 状态：规划待执行；每项修复独立提交、独立全量验证

## 总览

| ID | 债务 | 优先级 | 依赖 | 工作量估计 |
|----|------|--------|------|-----------|
| D1 | 配置文件格式混用（.toml 实为 YAML） | P2 | 无 | ~半天 |
| D2 | 真实湖合同测试 skip 恢复 + 深度增强 | P1 | **P0-① 数据湖落盘** | ~2 小时 |
| D3 | deployment 文件可移植性（硬编码机器路径） | P3 | 无 | ~1 小时 |
| D4 | ruff 存量 lint 债 364 项分批清理 | P3 | 无 | 3 批 × 2-4 小时 |
| D5 | 审查 P2 残余测试深度项 | P3 | 无 | ~2 小时 |
| D6 | 工作区噪音清理（gitignored 历史文档） | P3 | 无 | ~10 分钟 |

**排期原则**：D1/D4/D5 可与 P0 主线并行；D2 必须在 P0-①（批准池 61 只 qfq 落盘）完成后立即执行；D3 在下一次换机或部署前完成即可。

---

## D1 — 配置文件格式统一（真 TOML）

**现状**
- `inputs/configs/pipeline.toml`、`data_source.toml`、`profiles/model_mtl.toml` 内容是 YAML，
  由 `yaml.safe_load` 解析（`scripts/daily_pipeline.py:_load_yaml`、`scripts/train_mtl.py:57`）
- `profiles/sequence_dataset_baseline.toml`、`market_state_dataset_baseline.toml` 是真 TOML，
  由 `scripts/config_io.py`（tomllib）解析
- 两类解析器并存，扩展名与格式脱钩，`tomllib` 合同测试无法覆盖全部 configs

**修复步骤**
1. 三个 YAML 文件逐一手工转换为真 TOML（`key = value`、`[section]`，数组 `[...]`）
2. `daily_pipeline.py`：`_load_yaml` → `_load_config`（tomllib，py3.11 内置）；去掉 yaml 依赖
3. `train_mtl.py:57`：yaml.safe_load → tomllib；`test_model_mtl_yaml_parses` 改名同步
4. 新增合同测试：`inputs/configs/**/*.toml` 全部必须可被 `tomllib.loads` 解析
5. 验证：`daily_pipeline --dry-run`、`train_mtl --dry-run`、全量测试

**风险**：多行字符串/注释风格转换；转换后与 `scripts/config_io.py` 的 allowed-keys 校验兼容性。

**验收**：全量绿 + 新合同测试红→绿 + grep 确认 `yaml.safe_load` 不再解析 .toml。

---

## D2 — 真实湖合同测试恢复与增强（依赖 P0-①）

**现状**
- `tests/contract/infra/test_r4_cache_schema_contract.py` 在 `inputs/data/cache` 缺失时 **10 项全部 skip**
- 仅抽查池中第一个 symbol；历史起点断言只保证"不早于 2023"，允许严重缺数
- 10 个 skip 意味着真实数据落地后若有 schema 漂移，CI 依然不会变红

**修复步骤**（P0-① 落盘后立即执行）
1. 移除 skip 条件（改为硬性要求 cache root 存在；CI 中显式化 skip 原因）
2. 遍历全部 symbols 与全部分区文件（不再只查第一个）
3. 锁定历史起点：首个交易日必须 ≈ 2023-01 首个交易日（合理容差），并检查窗口连续性
4. 交叉校验 manifest（若存在）与分区文件集合一致
5. 与 D5 的 fixture 合同测试形成互补（committed fixture 永不 skip + 真实湖落地后硬断言）

**验收**：落盘后 10 项 skip → 10 项真实通过；人为注入 schema 漂移可被拦截。

---

## D3 — deployment 文件可移植性

**现状**
- `deployment/daily-pipeline.service` 硬编码 `/mnt/e/repos/WSL/personal/T1.AI`（本机路径）
- 换机/换路径即失效；`TUSHARE_TOKEN=your_token_here` 占位符无安装期校验
- `crontab.example` 需复查路径引用

**修复步骤**
1. service 内路径改为 `PROJECT_ROOT` 占位符 + 注释
2. 新增 `deployment/install.sh`：以参数/环境变量接收部署机路径，sed 生成最终 service 并校验 TUSHARE_TOKEN 非占位
3. `test_deployment_files.py` 增断言：service 含占位符、install.sh 存在且含替换逻辑
4. `docs/guides/daily_pipeline_ops.md` 部署段补充 install.sh 用法

**验收**：换路径部署只需跑 install.sh；测试锁定占位符机制。

---

## D4 — ruff 存量 lint 债（364 项）分批清理

**现状分布**（ruff 0.5→0.16 升级暴露，本次改动零新增）：

| 规则 | 数量 | 类型 |
|------|------|------|
| I001 unsorted-imports | 55 | 机械可修（*） |
| RUF100 unused-noqa | 53 | 机械可修（*），需复核 noqa 是否仍必要 |
| F401 unused-import | 37 | 手动（需确认无副作用导入） |
| UP035 deprecated-import | 33 | 手动（typing 导入迁移） |
| RUF046 unnecessary-cast-to-int | 32 | 手动 |
| BLE001 blind-except | 20 | 语义判断（逐处决定加 Exception 类型或 noqa） |
| DTZ005/DTZ007 时区 | 23 | 语义判断（量化代码时区约定） |
| 其余（TRY004/B009/UP006/PLR0402/FLY002/SIM118/SIM102） | ~111 | 混合 |

**分批方案**
- **批 A（机械）**：`ruff check --fix --select I001,B009,UP006,PLR0402` + RUF100 人工复核删除/保留
- **批 B（手动小修）**：F401/UP035/RUF046/SIM118/FLY002/SIM102，逐文件小改
- **批 C（语义决策）**：BLE001/TRY004/DTZ005/DTZ007 逐处评审；量化系统对时区的约定需先明确（建议：统一"naive 北京时间"并加注释或 per-file-ignores）

**铁律**：每批独立提交；每批后全量测试 + 覆盖率不回退；禁止与功能改动混合。

**验收**：ruff 计数归零（或剩余项全部有明确 noqa 理由）；CI 若引入 ruff 门禁则不阻塞。

---

## D5 — 审查 P2 残余测试深度项

| 项 | 内容 | 来源 |
|----|------|------|
| 5.1 | validator 适配器测试用 `assert_has_calls` 锁定 source/adjust/token/refresh/调用次数与顺序（当前只记 symbol） | Cx1#11 |
| 5.2 | `test_infra_a_flow` 改用真实 `load_or_fetch_daily_bars` 消费 fixture（当前内联重实现生产读取器，无法证明分区读取契约） | Pi1#16 / Cx1#10 |
| 5.3 | 动态 fixture 增加一个明确的交易日缺口用例（周末缺口），当前连续自然日无法暴露日历假设 | Cx1#13 残余 |
| 5.4 | `test_r4_cache_schema_contract` 全 parts 遍历与起点锁定 → 并入 D2 | Cx2#14 |

**验收**：逐项补测后全量绿；5.2 落地后 seeded fixture 被生产读取器真正消费。

---

## D6 — 工作区噪音清理（可选）

- `.claude/specs/**`、`.autoworkflow/state.md` 等 **gitignored** 历史文档仍含 akshare/旧路径字样
- 仅本机噪音，不影响仓库与 CI；确认无用途后本地删除即可（不入提交）

---

## 与主线的关系

```
P0-① 数据湖落盘（批准池 61 只 limited-live）
   └─→ D2 立即执行（skip→硬断言 + 深度增强）
P0 主线（评估范式固化 + 伪信号排查） ⇄ D1/D4/D5 并行穿插
D3 在下次换机/部署前完成
```
