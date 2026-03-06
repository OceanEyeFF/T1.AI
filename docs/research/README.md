# Research 文档

这一层放研究方法、评估工作流、训练策略和当前实验结论。

适合在这里回答的问题：

- 当前默认训练策略是什么
- 评估指标和门禁是什么
- 某个实验结论是否已经足够稳定
- 伪信号和泄漏风险在哪里

## 推荐阅读顺序

1. [research_checklist.md](research_checklist.md)
2. [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)
3. [数据窗口结构的区别.md](%E6%95%B0%E6%8D%AE%E7%AA%97%E5%8F%A3%E7%BB%93%E6%9E%84%E7%9A%84%E5%8C%BA%E5%88%AB.md)
4. [多头输出和数据切分.md](%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)
5. [警惕伪信号.md](%E8%AD%A6%E6%83%95%E4%BC%AA%E4%BF%A1%E5%8F%B7.md)
6. [IC评估体系最小改造清单与计划.md](IC%E8%AF%84%E4%BC%B0%E4%BD%93%E7%B3%BB%E6%9C%80%E5%B0%8F%E6%94%B9%E9%80%A0%E6%B8%85%E5%8D%95%E4%B8%8E%E8%AE%A1%E5%88%92.md)

## 文档分组

- [research_checklist.md](research_checklist.md)：研究主清单与门禁
- [daily_cs_eval_workflow.md](daily_cs_eval_workflow.md)：Daily-CS 评估流程
- [数据窗口结构的区别.md](%E6%95%B0%E6%8D%AE%E7%AA%97%E5%8F%A3%E7%BB%93%E6%9E%84%E7%9A%84%E5%8C%BA%E5%88%AB.md)：训练窗口与重训策略
- [多头输出和数据切分.md](%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md)：默认多头配置与固定切分数值
- [警惕伪信号.md](%E8%AD%A6%E6%83%95%E4%BC%AA%E4%BF%A1%E5%8F%B7.md)：伪信号与回测偏差风险
- [IC评估体系最小改造清单与计划.md](IC%E8%AF%84%E4%BC%B0%E4%BD%93%E7%B3%BB%E6%9C%80%E5%B0%8F%E6%94%B9%E9%80%A0%E6%B8%85%E5%8D%95%E4%B8%8E%E8%AE%A1%E5%88%92.md)：专项改造任务
- [IC评估体系改造Prompt包.md](IC%E8%AF%84%E4%BC%B0%E4%BD%93%E7%B3%BB%E6%94%B9%E9%80%A0Prompt%E5%8C%85.md)：执行辅助材料

## 当前默认训练策略入口

- 默认口径见 [数据窗口结构的区别.md](%E6%95%B0%E6%8D%AE%E7%AA%97%E5%8F%A3%E7%BB%93%E6%9E%84%E7%9A%84%E5%8C%BA%E5%88%AB.md) 的“`9. 本项目当前采用的训练策略（2026-03-06 修订）`”。
- 默认多头与切分数值见 [多头输出和数据切分.md](%E5%A4%9A%E5%A4%B4%E8%BE%93%E5%87%BA%E5%92%8C%E6%95%B0%E6%8D%AE%E5%88%87%E5%88%86.md) 的“`七、本项目默认口径（2026-03-06 定稿）`”。
- 关键规则是：`weekly retrain + daily inference + maturity-gated training pool + walk-forward evaluation`。
- 防偏差核对项见 [research_checklist.md](research_checklist.md) 的“`6. 防偏差检查`”。

## 历史实验

旧实验报告与旧消融文档已删除，不再保留仓库入口。  
如需追溯历史过程，应从版本历史检索。

## 外部材料

- [A股短中线预测IC提升方案：诊断与可执行研究计划.pdf](A%E8%82%A1%E7%9F%AD%E4%B8%AD%E7%BA%BF%E9%A2%84%E6%B5%8BIC%E6%8F%90%E5%8D%87%E6%96%B9%E6%A1%88%EF%BC%9A%E8%AF%8A%E6%96%AD%E4%B8%8E%E5%8F%AF%E6%89%A7%E8%A1%8C%E7%A0%94%E7%A9%B6%E8%AE%A1%E5%88%92.pdf)
- [A股短中线多头预测的 IC 提升与评估体系可执行研究计划.pdf](A%E8%82%A1%E7%9F%AD%E4%B8%AD%E7%BA%BF%E5%A4%9A%E5%A4%B4%E9%A2%84%E6%B5%8B%E7%9A%84%20IC%20%E6%8F%90%E5%8D%87%E4%B8%8E%E8%AF%84%E4%BC%B0%E4%BD%93%E7%B3%BB%E5%8F%AF%E6%89%A7%E8%A1%8C%E7%A0%94%E7%A9%B6%E8%AE%A1%E5%88%92.pdf)

## 使用边界

- 研究层不直接覆盖接口层文档。
- 任一研究结论进入主流程前，必须同步到 [../interfaces/README.md](../interfaces/README.md) 或 [../overview/README.md](../overview/README.md) 中对应文档。
