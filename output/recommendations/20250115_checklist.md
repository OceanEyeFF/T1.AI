# 人工检查报告（20250115）

**检查时间：** 2026-01-16 15:52:13

## 检查清单

- ✅ 3个时间跨度都有10只股票
- ✅ 推荐股票符合股票池过滤规则（无ST/科创/创业/北交）
- ✅ 预测收益率数值合理（无±100%等异常值）
- ✅ 推荐理由合理（包含 RSI/动量/量比 等特征提示）
- ✅ 输出格式正确（JSON/CSV/Markdown 可解析）

## 统计摘要

| horizon   |   count |   unique | allowed_all   | no_st_all   |   pred_min |   pred_max |   pred_abs_max | sample_reason                      |
|:----------|--------:|---------:|:--------------|:------------|-----------:|-----------:|---------------:|:-----------------------------------|
| 3d        |      10 |       10 | True          | True        | -0.173579  | -0.158282  |      0.173579  | RSI 24.0 | 20日动量 -19.3% | 量比 0.88x |
| 5d        |      10 |       10 | True          | True        | -0.160642  | -0.151476  |      0.160642  | RSI 24.0 | 20日动量 -19.3% | 量比 0.88x |
| 10d       |      10 |       10 | True          | True        | -0.0792339 | -0.0554067 |      0.0792339 | RSI 66.3 | 20日动量 8.4% | 量比 1.48x   |

## Top-1 推荐理由示例

- 3D: RSI 24.0 | 20日动量 -19.3% | 量比 0.88x
- 5D: RSI 24.0 | 20日动量 -19.3% | 量比 0.88x
- 10D: RSI 66.3 | 20日动量 8.4% | 量比 1.48x

## 文件清单

- output/recommendations/20250115.json
- output/recommendations/20250115_3d.csv
- output/recommendations/20250115_5d.csv
- output/recommendations/20250115_10d.csv
- output/recommendations/20250115.md
- output/recommendations/20250115_run.log
