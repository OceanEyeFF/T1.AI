# 下一步工作安排（Next Steps）

> 2026-08-13 | 环境重建 + akshare 移除 + 深度清理后

## 当前状态

项目已完成 R2（三区布局）→ R3（旧文件清理）→ T1（测试体系）→ R4（TuShare 数据湖合同）。
2026-08 完成换机后的环境重建与工作流收敛：

- **环境**：`py311-private`（Python 3.11 + PyTorch cu130，RTX 3080 Ti GPU 可用）
- **数据源**：TuShare 单一信源（akshare 依赖与代码已完全移除）
- **清理**：旧 raw 缓存（`data/`）、5 个退役脚本、`.servo` 控制面已移除
- **测试**：1020 passed / 10 skipped，覆盖率 77.13%（门禁 76）

### 双路 CodeReview 已完成（2026-08-13）

CodeX(gpt-5.6-sol/max) + Pi SubAgent(deepseek-v4-pro) 对重构测试完整性双路审查：
5 个 P0 缺陷 + 1 个 P0 测试防护空洞全部修复，P1 缺口已补测，全量回归绿。
残余项见文末“已知债”。

### 已有资产

| 层 | 状态 |
|----|------|
| **数据层** | TuShare 单一信源；R4 湖合同冻结（qfq/daily_basic/moneyflow），但 `inputs/data/cache` **尚未落数据** |
| **选股池** | `research_liquidity_quality` 批准池（61 只，research_only）+ 旧 `low_manipulation` |
| **模型层** | ModelABC + registry，已注册 LSTM / XGBoost / Transformer 三种模型 |
| **评估层** | Daily-CS IC 评估 pipeline 可用，trade-like panel 评估可用 |
| **推荐层** | 趋势聚合 + 多 horizon 打分引擎可用 |
| **回测层** | `BacktestEngine` + `ashare_exec`（Decision → WeightMapper → Strategy）可用 |

### 当前未完成

- **数据湖落盘**：批准池 61 只的 qfq/daily_basic/moneyflow 缓存尚未拉取（R4 残余）
- **主线 (3d/5d/10d) 可信评估范式**尚未固化
- **伪信号系统性排查**尚未完成
- **1d 超短线**独立研究线尚未启动（需分钟级数据验证）
- **决策模型**的 I/O 协议尚未冻结
- **认证注册表** `workspace/registry/certified.json` 为空

## 已知债（不阻塞主线）

- `.toml` 后缀混用 YAML 内容（pipeline/data_source/model_mtl），解析器不统一
- 真实湖合同测试（test_r4_cache_schema_contract）在 `inputs/data/cache` 缺失时全部 skip（P0-① 落盘后恢复）
- deployment/*.service 路径按部署机修改
- ruff 存量 lint 债 364 项（ruff 0.5→0.16 升级暴露，未动）

---

## 下一步优先级

### P0：把主线预测做"可信"

1. **数据湖落盘**：对批准池 61 只执行 limited-live 拉取
   - 用 `make_r4_datalake` + 批准的 L2 限流（`inputs/configs/tushare_rate_limits.toml`）
   - 先 510300.SH 锚点 → 小批量验证 → 全池补洞
2. 固化评估范式：Daily-CS IC/RankIC、月胜率分布、trade-like Top-N 面板
3. 系统排查伪信号：
   - 标签起点对齐（t close → t+1 open）
   - shuffle / time reverse / lag-1 sanity check
   - 复权、停牌、涨跌停处理
4. LSTM / XGBoost 同窗比较

### P1：主线性信号优化

1. 窗口长度、重训频率、loss 权重实验
2. `pred_3d/pred_5d/pred_10d → alpha_score` 聚合契约固化
3. 认证模型配对 → `workspace/registry/certified.json`

### P2：扩展

1. `1d` 分钟级数据可用性验证
2. 决策模型 I/O 协议冻结
3. 生产调度监控（deployment/ 文件需同步到当前机器路径）

---

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
