# 数据契约（Data Contract）

目的：无论使用 akshare / tushare / 其它数据源，策略与回测只依赖统一的内部 schema。

## 1. 交易日历（Calendar）

字段：
- `date`：交易日（YYYY-MM-DD）

## 2. 日线行情（Daily Bars）

DataFrame 索引/字段约定：
- 索引：`date`（datetime64[ns]，按升序）
- 字段（必须）：
  - `open` `high` `low` `close`：复权口径必须一致（建议前复权 qfq）
  - `volume`：成交量（手/股，保持原始口径但需一致）
  - `amount`：成交额（RMB）
- 字段（可选）：
  - `is_halt`：是否停牌（bool）

## 3. 涨跌停价（Limits）

若数据源不给出，回测可在 V0 阶段按规则近似：
- 非 ST、非科创/创业：涨跌幅限制 10%
- `limit_up = prev_close * 1.10`
- `limit_down = prev_close * 0.90`

注意：更严谨做法应处理价格最小变动单位与四舍五入规则，V0 先用 2 位小数近似。

## 4. 基本面（Fundamentals）

要求：
- 必须使用“披露日”对齐（`announce_date`），禁止把报表期末值回填到更早日期。
- V0 可不接；V1 接入后策略/特征必须显式声明是否使用基本面。

## 5. 公告/新闻（Text Events，可选插件）

建议 schema：
- `event_time`：发布时间（尽量使用原始源时间戳）
- `source`：来源
- `raw_text`：原文（必须存档，支持复跑）
- `parsed`：结构化抽取结果（JSON：事件类型、方向、主体、金额/比例等）

