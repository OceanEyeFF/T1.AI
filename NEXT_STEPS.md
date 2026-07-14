# 下一步工作安排（Next Steps）

> 2026-07-14 | MS-R3-001 合入后精简版

## 当前状态

项目已完成 MS-R2-001（三区布局）与 MS-R3-001（旧文件深度清理 + 路径修测）。现在是重新出发阶段。

### 已有资产

| 层 | 状态 |
|----|------|
| **数据层** | TuShare（主）/ AkShare（备用），日线数据管线可用 |
| **选股池** | `low_manipulation` 策略已实现，基于五维低操纵度筛选框架 |
| **模型层** | ModelABC + registry，已注册 LSTM / XGBoost / Transformer 三种模型 |
| **评估层** | Daily-CS IC 评估 pipeline 可用，trade-like panel 评估可用 |
| **推荐层** | 趋势聚合 + 多 horizon 打分引擎可用 |
| **回测层** | BacktestEngine + PortfolioManager 基础版本可用 |

### 当前未完成

- **主线 (3d/5d/10d) 可信评估范式**尚未固化
- **伪信号系统性排查**尚未完成
- **1d 超短线**独立研究线尚未启动（需分钟级数据验证）
- **决策模型**的 I/O 协议尚未冻结
- **TuShare 数据湖**（planned：MS-R4-001）尚未启动

---

## 下一步优先级

### P0：把主线预测做"可信"

1. 固化评估范式：Daily-CS IC/RankIC、月胜率分布、trade-like Top-N 面板
2. 系统排查伪信号：
   - 标签起点对齐（t close → t+1 open）
   - shuffle / time reverse / lag-1 sanity check
   - 复权、停牌、涨跌停处理
3. LSTM / XGBoost 同窗比较

### P1：主线性信号优化

1. 窗口长度、重训频率、loss 权重实验
2. `pred_3d/pred_5d/pred_10d → alpha_score` 聚合契约固化
3. 认证模型配对 → `workspace/registry/certified.json`

### P2：扩展

1. `1d` 分钟级数据可用性验证
2. 决策模型 I/O 协议冻结
3. TuShare 数据湖（MS-R4-001）与生产调度监控

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
