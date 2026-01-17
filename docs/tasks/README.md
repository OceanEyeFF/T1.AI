# 任务组织结构说明

本目录包含多时间跨度股票推荐系统的详细开发任务文档。

---

## 📁 文档结构

```
docs/tasks/
├── README.md                    # 本文档（任务组织说明）
├── phase1_core_features.md      # Phase 1: 核心功能补全（3-5天）
├── phase2_validation.md         # Phase 2: 验证与评估（2天）
└── phase3_automation.md         # Phase 3: 自动化与生产化（2-3天）
```

---

## 🎯 任务阶段概览

### ✅ 已完成：基础设施（85%）

- ✅ **数据层：** TuShare数据源 + 分区缓存 + 增量拉取
- ✅ **特征工程层：** 动量、斜率、相对交易量、技术指标（RSI/MACD/布林带）
- ✅ **标签层：** 多时间跨度标签（3D/5D/10D）+ 停牌检测
- ✅ **模型层：** MTL Transformer（共享编码器 + 3个独立回归头）
- ✅ **测试覆盖：** 125个单元测试全绿

---

### 🔲 Phase 1: 核心功能补全（3-5天）⭐⭐⭐

**目标：** 实现端到端推荐系统MVP，生成首个3×Top-10推荐榜单

**详细任务：** 参见 [phase1_core_features.md](./phase1_core_features.md)

#### 核心交付物

| 交付物 | 说明 |
|--------|------|
| `src/ashare_lab/dataset/sequence_builder.py` | 序列数据集构建器 |
| `src/ashare_lab/recommendation/engine.py` | 推荐引擎 |
| `scripts/train_mtl.py` | MTL训练脚本 |
| `scripts/generate_daily_recommendations.py` | 推荐生成脚本 |
| 首个3×Top-10推荐榜单 | JSON/CSV/Markdown格式 |

#### 验收标准

- ✅ MTL Transformer训练成功（验证集IC > 0.05）
- ✅ 成功生成3个独立推荐榜单（3D/5D/10D各Top-10）
- ✅ 输出格式正确（JSON/CSV/Markdown）
- ✅ 所有新增单元测试通过（≥ 10个）

---

### 🔲 Phase 2: 验证与评估（2天）⭐⭐

**目标：** 验证推荐系统准确性，建立历史推荐管理机制

**详细任务：** 参见 [phase2_validation.md](./phase2_validation.md)

#### 核心交付物

| 交付物 | 说明 |
|--------|------|
| `src/ashare_lab/recommendation/validator.py` | 推荐验证器 |
| `src/ashare_lab/recommendation/history.py` | 历史推荐管理 |
| `scripts/validate_recommendations.py` | 验证脚本 |
| `scripts/evaluate_recommendation.py` | 评估脚本 |
| 月度统计报告 | Markdown格式 |

#### 验收标准

- ✅ 推荐验证器正常工作（计算命中率/IC/超额收益）
- ✅ 历史推荐数据成功持久化（SQLite）
- ✅ 月度统计报告生成成功
- ✅ 验证指标数值合理（IC ∈ [-1, 1]，命中率 ∈ [0, 1]）

---

### 🔲 Phase 3: 自动化与生产化（2-3天）⭐⭐

**目标：** 实现每日自动化流程，无人工干预自动运行

**详细任务：** 参见 [phase3_automation.md](./phase3_automation.md)

#### 核心交付物

| 交付物 | 说明 |
|--------|------|
| `scripts/daily_pipeline.py` | 每日完整自动化流程 |
| `configs/data_source.yaml` | 数据源配置文件 |
| `configs/cron_job.sh` | Cron定时任务脚本 |
| `src/ashare_lab/monitoring/model_monitor.py` | 模型监控模块 |
| `docs/deployment.md` | 部署文档 |

#### 验收标准

- ✅ 每日Pipeline成功运行（数据拉取 → 推荐 → 验证 → 监控）
- ✅ 增量训练自动执行（每周一次）
- ✅ Cron定时任务正常触发（工作日15:15）
- ✅ 连续运行3日无报错

---

## 📊 总体进度

| 阶段 | 状态 | 完成度 | 预计工作量 |
|------|------|--------|-----------|
| 基础设施 | ✅ 已完成 | 85% | - |
| Phase 1 | 🔲 待开始 | 0% | 3-5天 |
| Phase 2 | 🔲 待开始 | 0% | 2天 |
| Phase 3 | 🔲 待开始 | 0% | 2-3天 |
| **总计** | **进行中** | **27%** | **7-10天** |

---

## 🚀 快速开始

### 查看当前任务

1. 打开对应的Phase文档（phase1/2/3_*.md）
2. 查看任务概览表格，了解任务依赖关系
3. 按照任务ID顺序执行

### 执行任务

1. **阅读详细任务说明** - 每个任务都有详细的实现指导
2. **编写代码** - 按照代码示例和接口定义实现功能
3. **编写单元测试** - 确保代码质量
4. **运行验收检查** - 对照验收标准检查功能完整性
5. **更新文档** - 标记任务状态（✅已完成 / 🔲待开始 / ⏳进行中）

### 更新TODO清单

完成一个Phase后，更新根目录的TODO清单：

```bash
# 在Claude Code中使用TodoWrite工具
# 将对应的Phase状态从 "pending" 改为 "completed"
```

---

## 📝 任务追踪规范

### 任务状态标记

- 🔲 **待开始** - 尚未启动
- ⏳ **进行中** - 正在开发
- ✅ **已完成** - 已完成并通过验收
- ⚠️ **阻塞** - 遇到问题需要解决

### 更新文档

每完成一个任务，在对应的Phase文档中：

1. 修改任务状态（状态列）
2. 添加实现笔记（可选）
3. 记录遇到的问题和解决方案（可选）

---

## 🎓 参考文档

- **主设计文档：** [docs/multi_horizon_stock_recommendation.md](../multi_horizon_stock_recommendation.md)
- **项目指南：** [CLAUDE.md](../../CLAUDE.md)
- **开发路线图：** [ROADMAP.md](../../ROADMAP.md)

---

## 💡 提示与建议

### 开发优先级

1. **优先完成Phase 1** - 这是端到端流程的基础
2. **快速验证功能** - 每完成一个模块立即测试
3. **先跑通再优化** - MVP优先，细节优化放在后期

### 常见问题

**Q: 发现新任务需要添加怎么办？**
A: 在对应Phase文档中追加任务，并更新任务概览表格

**Q: 任务依赖关系复杂怎么办？**
A: 查看任务概览表格的"依赖"列，按依赖顺序执行

**Q: 遇到技术难题怎么办？**
A: 先标记为"阻塞"状态，在文档中记录问题，寻求帮助或调整方案

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-15
**版本：** v1.0
